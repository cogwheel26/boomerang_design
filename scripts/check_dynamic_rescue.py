#!/usr/bin/env python3
"""Reproduce dynamic rescue vectors and check a bounded SAR acceptance model.

Requires Python 3 and cryptography. The SQLite model exercises transactional
acceptance and restart, with an external expected-history witness for restore
checks. The registration tuple is the dynamic rescue data component of
SetupPhoneSarMessage2; payment and static-data handling are outside this model.
It is not a SAR implementation, transport test, power-loss test, or acknowledgment
timing measurement. Test-only Schnorr code is not constant-time.
Run with --write-vectors to intentionally update the vector artifact.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from hashlib import sha256
import hmac
import json
from pathlib import Path
import sqlite3
import sys
import tempfile

from cryptography.hazmat.primitives import cmac, padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
sys.dont_write_bytecode = True
from generate_wire_catalog import Catalog, CatalogError, load_catalog

ROOT = Path(__file__).resolve().parents[1]
VECTOR_PATH = ROOT / 'outside/test_vectors' / f'{Path(__file__).stem.removeprefix("check_")}_vectors.json'
CATALOG = load_catalog(ROOT / 'spec/wire_catalog.json')
# Focused test-profile bound; SPEC Section 8.3 leaves v1 numeric limits open.
MAX_PAYLOAD = 65536
DOMAIN = 'Boomerang/setup/sar_dynamic_receipt'
# The repository's global PROTOCOL_VERSION assignment is still open. This is
# an explicit test profile, not an allocation of the production version/type.
PROFILE = b'\x11\x00\x01'  # canonical u16(1)
P = 2**256 - 2**32 - 977
N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
G = (0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798,
     0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8)


def require(condition, reason='check failed'):
    if not condition:
        raise ValueError(reason)


def tagged(label, data):
    t = sha256(label.encode()).digest()
    return sha256(t + t + data).digest()


def add(a, b):
    if a is None:
        return b
    if b is None:
        return a
    x, y = a
    u, v = b
    if x == u and (y + v) % P == 0:
        return None
    slope = ((3*x*x) * pow(2*y, -1, P) if a == b
             else (v-y) * pow((u-x) % P, -1, P)) % P
    r = (slope*slope-x-u) % P
    return r, (slope*(x-r)-y) % P


def mul(k, point=G):
    result = None
    while k:
        if k & 1:
            result = add(result, point)
        point = add(point, point)
        k >>= 1
    return result


def b32(n):
    return n.to_bytes(32, 'big')


def schnorr_sign(secret, message):
    x, y = mul(secret)
    d = secret if y % 2 == 0 else N-secret
    aux = tagged('BIP0340/aux', bytes(32))
    t = bytes(a ^ b for a, b in zip(b32(d), aux))
    k = int.from_bytes(tagged('BIP0340/nonce', t+b32(x)+message), 'big') % N
    require(k != 0)
    rx, ry = mul(k)
    k = k if ry % 2 == 0 else N-k
    e = int.from_bytes(tagged('BIP0340/challenge', b32(rx)+b32(x)+message), 'big') % N
    return b32(rx)+b32((k+e*d) % N)


def schnorr_verify(pubkey, message, signature):
    if len(pubkey) != 33 or pubkey[0] not in (2, 3) or len(signature) != 64:
        return False
    x = int.from_bytes(pubkey[1:], 'big')
    if x >= P:
        return False
    y = pow((x*x*x+7) % P, (P+1)//4, P)
    if y*y % P != (x*x*x+7) % P:
        return False
    y = y if y % 2 == 0 else P-y
    r, s = int.from_bytes(signature[:32], 'big'), int.from_bytes(signature[32:], 'big')
    if r >= P or s >= N:
        return False
    e = int.from_bytes(tagged('BIP0340/challenge', signature[:32]+b32(x)+message), 'big') % N
    point = add(mul(s), mul((N-e) % N, (x,y)))
    return point is not None and point[1] % 2 == 0 and point[0] == r


def fixed(data):
    return bytes({16: [0x22], 32: [0x23], 33: [0x24], 64: [0x25]}[len(data)])+data


def u64(value):
    require(0 <= value < 1 << 64, 'upload sequence range')
    return b'\x13'+value.to_bytes(8,'big')


def blob(data):
    return b'\x20'+len(data).to_bytes(4, 'big')+data


def text(value):
    data = value.encode('ascii')
    return b'\x21'+len(data).to_bytes(4, 'big')+data


def tup(*values):
    return b'\x31'+len(values).to_bytes(2, 'big')+b''.join(values)


def struct(name, values):
    schema = CATALOG.schema_by_name[name]
    require(len(values) == len(schema['fields']))
    return (b'\x40'+schema['id'].to_bytes(2, 'big')+b'\x00\x01'
            +len(values).to_bytes(2, 'big')
            +b''.join(f['id'].to_bytes(2, 'big')+v for f,v in zip(schema['fields'],values)))


# A separate strict decoder uses fixed normative schema assignments so catalog
# renumbering or field-order drift cannot silently regenerate accepted vectors.
LAYOUTS = {
    1: ('u8','bytes16','bytes','bytes16'),
    2: ('bytes33','text','receipt','bytes64'),
    11: ('bytes32','bytes32','bytes32','u64','envelope','bytes16'),
    30: ('bytes32','bytes32','bytes32','u64','bytes32'),
}


def decode(data, kind):
    def read(offset, expected):
        require(offset < len(data), 'truncated')
        if expected in ('envelope','upload','receipt','signed'):
            sid = {'envelope':1,'signed':2,'upload':11,'receipt':30}[expected]
            fields = LAYOUTS[sid]
            header = b'\x40'+sid.to_bytes(2,'big')+b'\x00\x01'+len(fields).to_bytes(2,'big')
            require(data[offset:offset+7] == header, 'schema')
            offset += 7
            values = []
            for index, field in enumerate(fields,1):
                require(data[offset:offset+2] == index.to_bytes(2,'big'), 'field order')
                value, offset = read(offset+2,field)
                values.append(value)
            return tuple(values),offset
        if expected == 'registration':
            require(data[offset:offset+3] == b'\x31\x00\x02','tuple')
            key, offset = read(offset+3,'bytes32')
            upload, offset = read(offset,'upload')
            return (key,upload),offset
        tag, size = {'u8':(0x10,1),'u64':(0x13,8),'bytes16':(0x22,16),'bytes32':(0x23,32),
                     'bytes33':(0x24,33),'bytes64':(0x25,64),
                     'bytes':(0x20,None),'text':(0x21,None)}[expected]
        require(data[offset] == tag,'tag')
        offset += 1
        if size is None:
            require(offset+4 <= len(data),'length')
            size = int.from_bytes(data[offset:offset+4],'big')
            offset += 4
        require(offset+size <= len(data),'truncated')
        result = data[offset:offset+size]
        if expected == 'u64':
            result = int.from_bytes(result,'big')
        return result,offset+size
    result, end = read(0,kind)
    require(end == len(data),'trailing bytes')
    return result


def mac(key, data):
    result = cmac.CMAC(algorithms.AES(key))
    result.update(data)
    return result.finalize()


def kdf(key, label, context, length):
    return b''.join(mac(key, i.to_bytes(4,'big')+label.encode()+b'\0'+context
                       +(8*length).to_bytes(4,'big'))
                    for i in range(1,(length+15)//16+1))[:length]


def device_key(root, device):
    return kdf(root,'Boomerang/sar_dynamic_device_data_key/v1',fixed(device),32)


def auth_key(root, account, profile=PROFILE):
    return kdf(root,'Boomerang/sar_dynamic_update_auth_key/v1',tup(profile,fixed(account)),32)


def context(account, device, upload_id, upload_seq_num, profile=PROFILE):
    return tup(text('Boomerang'),profile,text('sar_dynamic_data'),fixed(account),fixed(device),fixed(upload_id),u64(upload_seq_num))


def auth_preimage(account, device, upload_id, upload_seq_num, envelope, profile=PROFILE):
    return tup(text('Boomerang/sar_dynamic_upload/v1'),profile,fixed(account),fixed(device),fixed(upload_id),u64(upload_seq_num),envelope)


def envelope_bytes(env):
    version, iv, ciphertext, tag = env
    return struct('CbcCmacEnvelope',[b'\x10'+version,fixed(iv),blob(ciphertext),fixed(tag)])


def make_upload(root, account, device, upload_id, upload_seq_num, payload, iv, profile=PROFILE):
    require(len(payload) <= MAX_PAYLOAD,'payload limit')
    dk = device_key(root,device)
    keys = kdf(dk,'Boomerang/cbc_cmac/key_schedule/v1',text('Boomerang/sar_stored_data'),64)
    ctx = context(account,device,upload_id,upload_seq_num,profile)
    pad = padding.PKCS7(128).padder()
    padded = pad.update(blob(payload))+pad.finalize()
    encryptor = Cipher(algorithms.AES(keys[:32]),modes.CBC(iv)).encryptor()
    ciphertext = encryptor.update(padded)+encryptor.finalize()
    tag_input = tup(text('Boomerang/cbc_cmac/envelope/v1'),blob(ctx),fixed(iv),blob(ciphertext))
    tag = mac(keys[32:],tag_input)
    envelope = envelope_bytes((b'\x01',iv,ciphertext,tag))
    auth_input = auth_preimage(account,device,upload_id,upload_seq_num,envelope,profile)
    credential = auth_key(root,account,profile)
    upload = struct('DynamicRescueUpload',[fixed(account),fixed(device),fixed(upload_id),u64(upload_seq_num),envelope,fixed(mac(credential,auth_input))])
    return upload, {'device_data_key':dk,'cbc_key':keys[:32],'cmac_key':keys[32:],
                    'dynamic_update_auth_key':credential,'envelope_context':ctx,
                    'canonical_plaintext':blob(payload),'iv':iv,'ciphertext':ciphertext,
                    'envelope_cmac_input':tag_input,'envelope_cmac':tag,'envelope':envelope,
                    'upload_cmac_input':auth_input,'upload_cmac':mac(credential,auth_input)}


def validate_upload(upload, credential, profile=PROFILE):
    require(len(upload) <= 65752,'upload limit')
    account,device,upload_id,upload_seq_num,env,auth = decode(upload,'upload')
    version,iv,ciphertext,tag = env
    require(version == b'\x01' and 0 < len(ciphertext) <= 65552 and len(ciphertext)%16 == 0,'envelope bounds')
    preimage = auth_preimage(account,device,upload_id,upload_seq_num,envelope_bytes(env),profile)
    require(hmac.compare_digest(auth,mac(credential,preimage)),'authentication')
    return account,device,upload_id,upload_seq_num,env


def decrypt_payload(root, upload, profile=PROFILE):
    account,device,upload_id,seq,env,_ = decode(upload,'upload')
    _,iv,ciphertext,tag = env
    keys = kdf(device_key(root,device),'Boomerang/cbc_cmac/key_schedule/v1',text('Boomerang/sar_stored_data'),64)
    ctx = context(account,device,upload_id,seq,profile)
    require(hmac.compare_digest(tag,mac(keys[32:],tup(text('Boomerang/cbc_cmac/envelope/v1'),blob(ctx),fixed(iv),blob(ciphertext)))),'inner authentication')
    dec = Cipher(algorithms.AES(keys[:32]),modes.CBC(iv)).decryptor()
    padded = dec.update(ciphertext)+dec.finalize()
    unpad = padding.PKCS7(128).unpadder()
    payload = decode(unpad.update(padded)+unpad.finalize(),'bytes')
    require(len(payload) <= MAX_PAYLOAD,'payload limit')
    return payload


SECRET = 3
SX, SY = mul(SECRET)
PUBKEY = bytes([2+SY%2])+b32(SX)


def make_receipt(upload, profile=PROFILE):
    account,device,upload_id,seq,env,_ = decode(upload,'upload')
    envelope_hash = sha256(envelope_bytes(env)).digest()
    receipt = struct('DynamicRescueReceipt',[fixed(account),fixed(device),fixed(upload_id),u64(seq),fixed(envelope_hash)])
    preimage = tup(profile,text(DOMAIN),receipt)
    digest = tagged('Boomerang/signature/v1',preimage)
    sig = schnorr_sign(SECRET,digest)
    signed = struct('SignedMessage',[fixed(PUBKEY),text(DOMAIN),receipt,fixed(sig)])
    return signed, {'receipt':receipt,'envelope_hash':envelope_hash,
                    'signature_preimage':preimage,'signature_digest':digest,'signature':sig}


def verify_receipt(signed, upload, profile=PROFILE, expected_key=PUBKEY):
    key,domain,fields,sig = decode(signed,'signed')
    require(key == expected_key and domain == DOMAIN.encode(),'receipt identity/domain')
    account,device,upload_id,seq,env,_ = decode(upload,'upload')
    require(fields == (account,device,upload_id,seq,sha256(envelope_bytes(env)).digest()),'receipt fields')
    receipt = struct('DynamicRescueReceipt',[fixed(fields[0]),fixed(fields[1]),fixed(fields[2]),u64(fields[3]),fixed(fields[4])])
    digest = tagged('Boomerang/signature/v1',tup(profile,text(DOMAIN),receipt))
    require(schnorr_verify(key,digest,sig),'receipt signature')


class Store:
    """Bounded single-process transactional acceptance model, not a service."""
    def __init__(self,path):
        self.db = sqlite3.connect(path)
        self.db.executescript('''
            PRAGMA synchronous=FULL;
            CREATE TABLE IF NOT EXISTS account (id BLOB PRIMARY KEY, key BLOB, profile BLOB);
            CREATE TABLE IF NOT EXISTS upload (account BLOB, device BLOB, id BLOB, seq BLOB, body BLOB, receipt BLOB,
              PRIMARY KEY(account,device,id));
        ''')

    def accept(self, upload, registration=None, registered_identifier=None, profile=PROFILE,
               fail_at=None, capacity=True):
        account = decode(upload,'upload')[0]
        with self.db:
            existing = self.db.execute('SELECT key,profile FROM account WHERE id=?',(account,)).fetchone()
            if registration is not None:
                require(registered_identifier == account,'registered identifier')
                if existing:
                    require(hmac.compare_digest(existing[0],registration) and existing[1] == profile,'registered key/profile')
                credential = registration
            else:
                require(existing is not None,'unregistered')
                credential,stored_profile = existing
                require(stored_profile == profile,'profile')
            a,d,upload_id,seq,_ = validate_upload(upload,credential,profile)
            if registration is not None:
                require(seq == 0, 'initial upload sequence')
            old = self.db.execute('SELECT body,receipt FROM upload WHERE account=? AND device=? AND id=?',(a,d,upload_id)).fetchone()
            if old:
                require(old[0] == upload,'conflict')
                return old[1]
            require(capacity,'capacity')
            if not existing:
                require(registration is not None,'registration required')
                self.db.execute('INSERT INTO account VALUES (?,?,?)',(a,credential,profile))
            require(fail_at != 'credential','interrupted credential write')
            receipt,_ = make_receipt(upload,profile)
            self.db.execute('INSERT INTO upload VALUES (?,?,?,?,?,?)',(a,d,upload_id,seq.to_bytes(8,'big'),upload,receipt))
            require(fail_at != 'append','interrupted append write')
        require(fail_at != 'reply','lost reply after commit')
        return receipt

    def history(self):
        return tuple(self.db.execute('SELECT body,receipt FROM upload ORDER BY account,device,seq,id'))

    def check_restoration(self, expected):
        # Independent expected witness is deliberately outside the restored DB.
        require(set(expected) <= set(self.history()),'incomplete restoration')


def rejects(fn):
    try:
        fn()
    except ValueError:
        return
    raise AssertionError('expected rejection')


def run():
    # Official BIP340 test vector 0; provenance retained in the JSON artifact.
    expected_sig = bytes.fromhex('E907831F80848D1069A5371B402410364BDF1C5F8307B0084C55F1CE2DCA821525F66A4A85EA8B71E482A74F382D2CE5EBEEE8FDB2172F477DF4900D310536C0')
    require(schnorr_sign(3,bytes(32)) == expected_sig,'BIP340 vector 0')
    require(schnorr_verify(PUBKEY,bytes(32),expected_sig))
    require(not schnorr_verify(PUBKEY,bytes([1])*32,expected_sig))
    root = bytes(range(32))
    account = tagged('Boomerang/doxing_data_identifier',root)
    device, upload_id, seq, iv = bytes(range(32,64)),bytes(range(64,96)),0,bytes(range(16))
    credential = auth_key(root,account)
    vectors=[]
    for index,(name,payload,dev,uid,upload_seq_num) in enumerate([
        ('observation',b'rescue observation',device,upload_id,seq),
        ('empty',b'',device,bytes([1])*32,1),
        ('padding_boundary',bytes(11),device,bytes([2])*32,2),
        ('replacement',b'correction',bytes([3])*32,upload_id,seq),
    ]):
        # Deterministic fixtures only; each upload under one device key gets a
        # distinct IV. Production uses random_bytes(16).
        fixture_iv = bytes([index])*16
        upload,parts = make_upload(root,account,dev,uid,upload_seq_num,payload,fixture_iv)
        receipt,receipt_parts = make_receipt(upload)
        require(decrypt_payload(root,upload) == payload)
        validate_upload(upload,credential)
        verify_receipt(receipt,upload)
        registration = tup(fixed(credential),upload)
        require(decode(registration,'registration')[0] == credential)
        require(len(receipt) == 312 and len(receipt_parts['receipt']) == 158)
        vectors.append({'name':name,'payload_hex':payload.hex(),'device_id':dev.hex(),
                        'upload_id':uid.hex(),'upload_seq_num':upload_seq_num,
                        **{k:v.hex() for k,v in parts.items()},
                        **{k:v.hex() for k,v in receipt_parts.items()},
                        'upload':upload.hex(),'registration_tuple':registration.hex(),'signed_upload_receipt':receipt.hex(),
                        'sizes':{'upload':len(upload),'registration':len(registration),'signed_upload_receipt':len(receipt)}})
    upload=bytes.fromhex(vectors[0]['upload']); receipt=bytes.fromhex(vectors[0]['signed_upload_receipt'])
    replacement=bytes.fromhex(vectors[-1]['upload'])
    conflict,_=make_upload(root,account,device,upload_id,seq,b'rescue observation',bytes([7])*16)
    sequence_conflict,_=make_upload(root,account,device,upload_id,1,b'rescue observation',bytes([7])*16)
    # Change each authenticated identity field, inner envelope, and CMAC.
    decoded=decode(upload,'upload')
    for offset in (10,45,80,115,170,len(upload)-1):
        changed=bytearray(upload); changed[offset] ^= 1
        rejects(lambda:validate_upload(bytes(changed),credential))
    wrong_sequence_type=bytearray(upload); wrong_sequence_type[114]=0x23
    rejects(lambda:validate_upload(bytes(wrong_sequence_type),credential))
    for bad in (upload+b'\0',upload[:-1],b'\x40\x00\x0c'+upload[3:],upload[:5]+b'\x00\x04'+upload[7:]):
        rejects(lambda:validate_upload(bad,credential))
    rejects(lambda:validate_upload(upload,bytes(32)))
    rejects(lambda:validate_upload(upload,credential,b'\x11\x00\x02'))
    rejects(lambda:verify_receipt(receipt,replacement))
    rejects(lambda:verify_receipt(receipt,sequence_conflict))
    rejects(lambda:verify_receipt(receipt,upload,b'\x11\x00\x02'))
    rejects(lambda:verify_receipt(receipt,upload,expected_key=b'\x02'+bytes(32)))
    # Wrong domain and signature, and an incorrectly shaped registration tuple.
    rejects(lambda:verify_receipt(receipt.replace(DOMAIN.encode(),b'X'*len(DOMAIN)),upload))
    rejects(lambda:verify_receipt(receipt[:-1]+bytes([receipt[-1]^1]),upload))
    rejects(lambda:decode(tup(blob(credential),upload),'registration'))
    maximum, _ = make_upload(root,account,device,upload_id,seq,bytes(MAX_PAYLOAD),iv)
    validate_upload(maximum,credential)
    require(len(decrypt_payload(root,maximum)) == MAX_PAYLOAD)
    require(len(maximum) == 65752 and len(tup(fixed(credential),maximum)) == 65788)
    rejects(lambda:make_upload(root,account,device,upload_id,seq,bytes(MAX_PAYLOAD+1),iv))
    oversized=struct('DynamicRescueUpload',[fixed(account),fixed(device),fixed(upload_id),u64(seq),
        envelope_bytes((b'\x01',iv,bytes(65568),bytes(16))),fixed(bytes(16))])
    rejects(lambda:validate_upload(oversized,credential))
    # A holder of upload authority may submit undecryptable bytes. Acceptance
    # remains payload-independent and rescue reports the per-entry failure.
    a,d,_,_,env,_=decoded
    damaged_env=envelope_bytes((env[0],env[1],env[2],bytes(16)))
    opaque_id=bytes([9])*32
    opaque_seq=2
    opaque=struct('DynamicRescueUpload',[fixed(a),fixed(d),fixed(opaque_id),u64(opaque_seq),damaged_env,
        fixed(mac(credential,auth_preimage(a,d,opaque_id,opaque_seq,damaged_env)))])
    validate_upload(opaque,credential)
    rejects(lambda:decrypt_payload(root,opaque))
    with tempfile.TemporaryDirectory(prefix='dynamic-rescue-') as tmp:
        path=Path(tmp)/'history.sqlite'
        store=Store(path)
        rejects(lambda:store.accept(upload))
        rejects(lambda:store.accept(upload,registration=credential,registered_identifier=bytes(32)))
        rejects(lambda:store.accept(upload,registration=bytes(32),registered_identifier=account))
        rejects(lambda:store.accept(bytes.fromhex(vectors[1]['upload']),registration=credential,registered_identifier=account))
        require(store.db.execute('SELECT count(*) FROM account').fetchone()[0] == 0)
        for point in ('credential','append'):
            rejects(lambda:store.accept(upload,registration=credential,registered_identifier=account,fail_at=point))
            require(store.db.execute('SELECT count(*) FROM account').fetchone()[0] == 0)
            require(store.history() == ())
        rejects(lambda:store.accept(upload,registration=credential,registered_identifier=account,fail_at='reply'))
        witness=store.history()
        require(len(witness) == 1)
        store.db.close(); store=Store(path)
        require(store.accept(upload,registration=credential,registered_identifier=account) == receipt)
        require(store.accept(upload,capacity=False) == receipt)
        rejects(lambda:store.accept(upload,registration=bytes(32),registered_identifier=account))
        rejects(lambda:store.accept(conflict))
        rejects(lambda:store.accept(sequence_conflict))
        rejects(lambda:store.accept(replacement,capacity=False))
        verify_receipt(store.accept(replacement),replacement)
        verify_receipt(store.accept(opaque),opaque)
        same_seq,_=make_upload(root,account,device,bytes([8])*32,2,b'real observation',bytes([8])*16)
        verify_receipt(store.accept(same_seq),same_seq)
        # Another upload from the original Phone appends without affecting the replacement.
        old_phone,_=make_upload(root,account,device,bytes([10])*32,1,b'later observation',bytes([10])*16)
        store.accept(old_phone)
        require(len(store.history()) == 5)
        original_history = [decode(body,'upload')[3] for body,_ in store.history()
                            if decode(body,'upload')[:2] == (account,device)]
        require(original_history == [0,1,2,2], 'late and duplicate sequence order')
        second_root = bytes([42])*32
        second_account = tagged('Boomerang/doxing_data_identifier',second_root)
        second_key = auth_key(second_root,second_account)
        second_upload,_ = make_upload(second_root,second_account,device,upload_id,seq,b'another account',iv)
        store.accept(second_upload,registration=second_key,registered_identifier=second_account)
        require(len(store.history()) == 6)
        store.check_restoration(witness)
        witness=store.history()
        # Restore an internally consistent but incomplete database; external witness detects loss.
        store.db.execute('DELETE FROM upload WHERE account=? AND device=? AND id=?',
                         (account,device,upload_id)); store.db.commit()
        rejects(lambda:store.check_restoration(witness))
        store.db.close()
        # Serializations of two concurrent conflicts admit only one accepted identity.
        for i,order in enumerate(((upload,conflict),(conflict,upload))):
            candidate=Store(Path(tmp)/f'conflict-{i}.sqlite')
            winner=candidate.accept(order[0],registration=credential,registered_identifier=account)
            rejects(lambda:candidate.accept(order[1]))
            require(candidate.accept(order[0]) == winner and len(candidate.history()) == 1)
            candidate.db.close()
        wide=Store(Path(tmp)/'wide-sequence.sqlite')
        wide.accept(upload,registration=credential,registered_identifier=account)
        wide_upload,_=make_upload(root,account,device,bytes([11])*32,(1<<64)-1,b'wide sequence',bytes([11])*16)
        wide.accept(wide_upload)
        require(decode(wide.history()[-1][0],'upload')[3] == (1<<64)-1)
        wide.db.close()
        rejects(lambda:make_upload(root,account,device,bytes([12])*32,1<<64,b'overflow',iv))
    # Exercise schema ID uniqueness, ordering, and continuity.
    for mutate in (
        lambda c:c['schemas'][-1].update(id=11),
        lambda c:c['schemas'][-1].update(id=31),
        lambda c:c['schemas'][-1].update(id=0),
    ):
        bad=deepcopy(CATALOG.data); mutate(bad)
        try:
            Catalog(Path('negative-catalog.json'),bad).validate()
        except CatalogError:
            pass
        else:
            raise AssertionError('invalid schema ID accepted')
    return {
        'scope':'Focused dynamic rescue vectors and bounded acceptance-model checks; not full v1 conformance.',
        'test_profile':{'PROTOCOL_VERSION_type':'u16','PROTOCOL_VERSION_value':1,'canonical_hex':PROFILE.hex(),
                        'production_assignment':'open; test profile only',
                        'payload_limit':'65536 bytes for this test profile only; v1 limit open'},
        'bip340_anchor':'https://github.com/bitcoin/bips/blob/master/bip-0340/test-vectors.csv (vector 0)',
        'inputs':{'doxing_key_for_sar':root.hex(),'doxing_data_identifier':account.hex(),
                  'sar_secret_key':b32(SECRET).hex(),'sar_public_key':PUBKEY.hex(),'bip340_aux_rand':bytes(32).hex()},
        'registration_tuple_scope':'Dynamic rescue data component of SetupPhoneSarMessage2; excludes payment receipts, identifier, and static envelope.',
        'vectors':vectors,
        'boundary':{'payload_pattern':'00 repeated payload_length times','payload_length':MAX_PAYLOAD,
                    'device_id':device.hex(),'upload_id':upload_id.hex(),
                    'upload_seq_num':seq,'iv':iv.hex(),
                    'canonical_plaintext_bytes':65541,'ciphertext_bytes':65552,'envelope_bytes':65608,
                    'upload_bytes':len(maximum),'registration_bytes':len(tup(fixed(credential),maximum)),
                    'upload_sha256':sha256(maximum).hexdigest(),'first_rejected_payload_length':65537,
                    'first_rejected_ciphertext_multiple':65568,'failure_class':'INVALID_ENCODING'},
        'scenarios':['registered-identifier precondition','atomic credential and append interruption',
                     'lost reply after commit','restart and original receipt','exact retry without new capacity',
                     'wrong credential and profile','authenticated changed-IV and sequence conflicts','both conflict serializations',
                     'replacement and old Phone append','out-of-order per-device acceptance',
                     'duplicate sequence under distinct upload IDs',
                     'device and account separation','u64 sequence boundary',
                     'opaque undecryptable payload retained',
                     'independent witness detects incomplete restore','strict canonical rejection','size boundaries',
                     'receipt signer/domain/profile/identity/signature rejection','schema ID checks'],
        'evidence_limits':['Registration binding and authenticated transport are assumed by the model.',
                           'Payment and static-data handling, including their commit with the dynamic records, are not modeled.',
                           'Phone first-submission sequencing and counter continuity are not modeled.',
                           'SQLite rollback/reopen does not test process kill, power loss, replication, or deployment durability.',
                           'Conflict serializations are checked; actual parallel transaction scheduling is not tested.',
                           'The external restoration witness is supplied by the checker, not a specified deployment mechanism.',
                           'Safe/duress timing, actual rescue delivery, and independent implementation reproduction remain open.']}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write-vectors',action='store_true')
    args=parser.parse_args()
    result=run()
    output=json.dumps(result,indent=2)+'\n'
    if args.write_vectors:
        VECTOR_PATH.write_text(output)
        print(f'Generated {VECTOR_PATH.relative_to(ROOT)}')
    else:
        require(VECTOR_PATH.read_text() == output,'vector drift: review changes before --write-vectors')
    print(f"PASS: {len(result['vectors'])} vectors, payload boundaries, {len(result['scenarios'])} scenario groups; bounded evidence only")


if __name__ == '__main__':
    main()

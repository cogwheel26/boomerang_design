#!/usr/bin/env python3
"""Generate the wire catalog report from the canonical JSON catalog."""

from __future__ import annotations

import argparse
import io
import json
import re
import sys
import textwrap
from contextlib import redirect_stdout
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG = ROOT / "spec" / "wire_catalog.json"
DEFAULT_REPORT = ROOT / "spec" / "wire_catalog.txt"
TAG_PATTERN = re.compile(r"0x[0-9A-Fa-f]{2}")
NAME_PATTERN = re.compile(r"[A-Za-z][A-Za-z0-9_]*")


class CatalogError(Exception):
    """Raised when the catalog is not structurally valid."""


@dataclass(frozen=True)
class TypeExpr:
    name: str
    args: tuple["TypeExpr", ...] = ()

    def __str__(self) -> str:
        if not self.args:
            return self.name
        return f"{self.name}<{', '.join(map(str, self.args))}>"


@dataclass(frozen=True)
class DepthResult:
    depth: int
    path: tuple[str, ...]
    unresolved_contexts: frozenset[str] = frozenset()


def split_type_arguments(value: str) -> list[str]:
    parts: list[str] = []
    start = 0
    depth = 0
    for index, character in enumerate(value):
        if character == "<":
            depth += 1
        elif character == ">":
            depth -= 1
            if depth < 0:
                raise ValueError("unmatched closing bracket")
        elif character == "," and depth == 0:
            parts.append(value[start:index].strip())
            start = index + 1
    if depth != 0:
        raise ValueError("unmatched opening bracket")
    parts.append(value[start:].strip())
    return parts


def parse_type(value: str) -> TypeExpr:
    value = value.strip()
    if not value:
        raise ValueError("empty type")
    bracket = value.find("<")
    if bracket < 0:
        if not NAME_PATTERN.fullmatch(value):
            raise ValueError(f"invalid type name {value!r}")
        return TypeExpr(value)
    if not value.endswith(">"):
        raise ValueError("missing closing bracket")
    name = value[:bracket]
    if not NAME_PATTERN.fullmatch(name):
        raise ValueError(f"invalid type name {name!r}")
    inner = value[bracket + 1 : -1]
    return TypeExpr(name, tuple(parse_type(part) for part in split_type_arguments(inner)))


def duplicate_values(values: Iterable[Any]) -> list[Any]:
    seen: set[Any] = set()
    duplicates: set[Any] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return sorted(duplicates, key=str)


class Catalog:
    def __init__(self, source: Path, data: dict[str, Any]):
        self.source = source
        self.data = data
        self.errors: list[str] = []
        self.primitives = self._records("primitives")
        self.header_scalars = self._records("header_scalars")
        self.containers = self._records("containers")
        self.schemas = self._records("schemas")
        constants = data.get("profile_constants", {})
        if not isinstance(constants, dict):
            self.errors.append("profile_constants must be an object")
            constants = {}
        self.profile_constants: dict[str, Any] = constants
        contexts = data.get("context_rules", {})
        if not isinstance(contexts, dict):
            self.errors.append("context_rules must be an object")
            contexts = {}
        self.contexts: dict[str, Any] = contexts
        encryption_contexts = data.get("encryption_contexts", {})
        if not isinstance(encryption_contexts, dict):
            self.errors.append("encryption_contexts must be an object")
            encryption_contexts = {}
        self.encryption_contexts: dict[str, Any] = encryption_contexts
        self.primitive_by_name = self._index(self.primitives, "primitive")
        self.scalar_by_name = self._index(self.header_scalars, "header scalar")
        self.container_by_name = self._index(self.containers, "container")
        self.schema_by_name = self._index(self.schemas, "schema")

    def _records(self, key: str) -> list[dict[str, Any]]:
        value = self.data.get(key)
        if not isinstance(value, list):
            self.errors.append(f"{key} must be an array")
            return []
        records: list[dict[str, Any]] = []
        for index, item in enumerate(value):
            if not isinstance(item, dict):
                self.errors.append(f"{key}[{index}] must be an object")
            else:
                records.append(item)
        return records

    def _index(
        self, records: list[dict[str, Any]], label: str
    ) -> dict[str, dict[str, Any]]:
        result: dict[str, dict[str, Any]] = {}
        for index, record in enumerate(records):
            name = record.get("name")
            if not isinstance(name, str) or not name:
                self.errors.append(f"{label} at index {index} has no valid name")
                continue
            if name in result:
                self.errors.append(f"duplicate {label} name {name}")
            result[name] = record
        return result

    def validate(self) -> None:
        self._validate_top_level()
        self._validate_tags_and_headers()
        self._validate_schemas()
        self._validate_contexts()
        self._validate_encryption_contexts()
        self._validate_cycles()
        if self.errors:
            raise CatalogError("\n".join(f"- {error}" for error in self.errors))

    def _validate_top_level(self) -> None:
        if self.data.get("catalog_format_version") != 1:
            self.errors.append("catalog_format_version must be 1")
        for name, value in self.profile_constants.items():
            if not NAME_PATTERN.fullmatch(name):
                self.errors.append(f"invalid profile constant name {name!r}")
            if not self._is_positive_integer(value):
                self.errors.append(f"profile constant {name} must be a positive integer")
        invariants = self.data.get("invariants")
        if not isinstance(invariants, dict):
            self.errors.append("invariants must be an object")
            return
        expected_rules = {
            "byte_order": "big_endian",
            "schema_version_zero": "reserved",
            "unsupported_schema_version": "reject",
            "field_id_zero": "reserved",
            "field_order": "ascending_id",
            "version_1_fields": "all_required",
            "null_tag": "reserved",
            "trailing_bytes": "reject",
            "dynamic_value_requires_exact_context": True,
        }
        for name, expected in expected_rules.items():
            if invariants.get(name) != expected:
                self.errors.append(
                    f"invariants.{name} is {invariants.get(name)!r}, expected {expected!r}"
                )

    def _validate_tags_and_headers(self) -> None:
        tags: list[str] = []
        reserved = self.data.get("reserved_tags", [])
        if not isinstance(reserved, list):
            self.errors.append("reserved_tags must be an array")
            reserved = []
        tags.extend(tag for tag in reserved if isinstance(tag, str))
        for primitive in self.primitives:
            if isinstance(primitive.get("tag"), str):
                tags.append(primitive["tag"])
            encodings = primitive.get("encodings", {})
            if isinstance(encodings, dict):
                tags.extend(value for value in encodings.values() if isinstance(value, str))
        tags.extend(
            container["tag"]
            for container in self.containers
            if isinstance(container.get("tag"), str)
        )
        for tag in tags:
            if not TAG_PATTERN.fullmatch(tag):
                self.errors.append(f"invalid one-byte tag {tag!r}")
        for tag in duplicate_values(tags):
            self.errors.append(f"duplicate tag {tag}")

        required_primitives = {
            "bool", "u8", "u16", "u32", "u64", "bytes", "text",
            "bytes16", "bytes32", "bytes33", "bytes64",
        }
        missing = sorted(required_primitives - self.primitive_by_name.keys())
        if missing:
            self.errors.append(f"missing primitives {', '.join(missing)}")
        required_containers = {"list", "tuple", "struct"}
        missing = sorted(required_containers - self.container_by_name.keys())
        if missing:
            self.errors.append(f"missing containers {', '.join(missing)}")

        type_name_overlap = sorted(
            self.primitive_by_name.keys() & self.schema_by_name.keys()
        )
        if type_name_overlap:
            self.errors.append(
                f"primitive and schema names overlap {', '.join(type_name_overlap)}"
            )

        expected_scalars = {
            "u16_raw": (2, "big_endian", False),
            "u32_raw": (4, "big_endian", False),
        }
        for name, expected in expected_scalars.items():
            scalar = self.scalar_by_name.get(name)
            if scalar is None:
                self.errors.append(f"missing header scalar {name}")
                continue
            actual = (
                scalar.get("encoded_size"),
                scalar.get("byte_order"),
                scalar.get("tagged"),
            )
            if actual != expected:
                self.errors.append(f"header scalar {name} must be {expected!r}")

        for primitive in self.primitives:
            name = primitive.get("name", "<unnamed>")
            if name == "bool":
                if set(primitive.get("encodings", {})) != {"false", "true"}:
                    self.errors.append("primitive bool must define false and true encodings")
            elif not isinstance(primitive.get("tag"), str):
                self.errors.append(f"primitive {name}.tag is missing")
            if "encoded_size" in primitive:
                if not self._is_positive_integer(primitive["encoded_size"]):
                    self.errors.append(f"primitive {name}.encoded_size must be positive")
            elif not self._is_positive_integer(primitive.get("header_bytes")):
                self.errors.append(f"primitive {name}.header_bytes must be positive")
            payload_bytes = primitive.get("payload_bytes")
            if self._is_positive_integer(payload_bytes):
                expected_size = 1 + payload_bytes
                if primitive.get("encoded_size") != expected_size:
                    self.errors.append(
                        f"primitive {name}.encoded_size must be {expected_size}"
                    )
            length_type = primitive.get("length_type")
            if length_type in self.scalar_by_name:
                expected_header = 1 + self.scalar_by_name[length_type]["encoded_size"]
                if primitive.get("header_bytes") != expected_header:
                    self.errors.append(
                        f"primitive {name}.header_bytes must be {expected_header}"
                    )

        for container in self.containers:
            name = container.get("name", "<unnamed>")
            if not isinstance(container.get("tag"), str):
                self.errors.append(f"container {name}.tag is missing")
            if not self._is_positive_integer(container.get("header_bytes")):
                self.errors.append(f"container {name}.header_bytes must be positive")
            count_type = container.get("count_type")
            if count_type in self.scalar_by_name:
                expected_header = 1 + self.scalar_by_name[count_type]["encoded_size"]
                if container.get("header_bytes") != expected_header:
                    self.errors.append(
                        f"container {name}.header_bytes must be {expected_header}"
                    )
        struct = self.container_by_name.get("struct", {})
        if not self._is_positive_integer(struct.get("field_header_bytes")):
            self.errors.append("container struct.field_header_bytes must be positive")
        struct_types = [
            struct.get("schema_id_type"),
            struct.get("schema_version_type"),
            struct.get("field_count_type"),
        ]
        if all(name in self.scalar_by_name for name in struct_types):
            expected_header = 1 + sum(
                self.scalar_by_name[name]["encoded_size"] for name in struct_types
            )
            if struct.get("header_bytes") != expected_header:
                self.errors.append(
                    f"container struct.header_bytes must be {expected_header}"
                )
        field_id_type = struct.get("field_id_type")
        if field_id_type in self.scalar_by_name:
            expected_field_header = self.scalar_by_name[field_id_type]["encoded_size"]
            if struct.get("field_header_bytes") != expected_field_header:
                self.errors.append(
                    f"container struct.field_header_bytes must be {expected_field_header}"
                )

        tagged_records = [
            (primitive, f"primitive {primitive.get('name')}")
            for primitive in self.primitives
        ]
        tagged_records.extend(
            (container, f"container {container.get('name')}")
            for container in self.containers
        )
        for record, label in tagged_records:
            for key, value in record.items():
                if key.endswith("_type") and value not in self.scalar_by_name:
                    self.errors.append(f"{label}.{key} references missing header scalar {value}")

    @staticmethod
    def _is_positive_integer(value: Any) -> bool:
        return isinstance(value, int) and not isinstance(value, bool) and value > 0

    def _validate_schemas(self) -> None:
        ids = [schema.get("id") for schema in self.schemas]
        for duplicate in duplicate_values(ids):
            self.errors.append(f"duplicate schema ID {duplicate}")
        if ids != list(range(1, len(self.schemas) + 1)):
            self.errors.append("schema IDs must be consecutive and ordered from 1")

        for schema in self.schemas:
            name = schema.get("name", "<unnamed>")
            if schema.get("version") != 1:
                self.errors.append(f"{name}.version must be 1")
            fields = schema.get("fields")
            if not isinstance(fields, list):
                self.errors.append(f"{name}.fields must be an array")
                continue
            if any(not isinstance(field, dict) for field in fields):
                self.errors.append(f"{name}.fields must contain only objects")
                continue
            field_ids = [field.get("id") for field in fields]
            for duplicate in duplicate_values(field_ids):
                self.errors.append(f"{name} has duplicate field ID {duplicate}")
            if field_ids != list(range(1, len(fields) + 1)):
                self.errors.append(f"{name} field IDs must be consecutive and ordered from 1")
            field_names = [field.get("name") for field in fields]
            for duplicate in duplicate_values(field_names):
                self.errors.append(f"{name} has duplicate field name {duplicate}")
            for field in fields:
                self._validate_field(schema, field)

    def _validate_field(self, schema: dict[str, Any], field: dict[str, Any]) -> None:
        location = f"{schema.get('name', '<unnamed>')}.{field.get('name', '<unnamed>')}"
        if field.get("required") is not True:
            self.errors.append(f"{location} must be required in schema version 1")
        type_name = field.get("type")
        if not isinstance(type_name, str):
            self.errors.append(f"{location}.type must be a string")
            return
        try:
            expression = parse_type(type_name)
        except ValueError as error:
            self.errors.append(f"{location}.type is invalid: {error}")
            return
        self._validate_type(expression, location, context_expression=False)
        if expression.name == "value" and not expression.args:
            rule = field.get("context_rule")
            if rule not in self.contexts:
                self.errors.append(f"{location} references missing context rule {rule!r}")
        elif "context_rule" in field:
            self.errors.append(f"{location} has a context rule but is not type value")
        if expression.name in {"bytes", "text"} and "max_payload_bytes" in field:
            self.errors.append(
                f"{location}.max_payload_bytes belongs in the normative SPEC limit registry"
            )
        if expression.name == "text" and "text_profile" not in field:
            self.errors.append(f"{location}.text_profile is missing")
        if expression.name == "list":
            has_exact = "exact_items" in field
            has_maximum = "max_items" in field
            if has_exact and has_maximum:
                self.errors.append(
                    f"{location} cannot define both exact_items and max_items"
                )
            elif has_maximum:
                self.errors.append(
                    f"{location}.max_items belongs in the normative SPEC limit registry"
                )
            elif has_exact:
                self._validate_exact_items(field["exact_items"], location)

    def _validate_exact_items(self, rule: Any, location: str) -> None:
        if not isinstance(rule, dict):
            self.errors.append(f"{location}.exact_items must be an object")
            return
        if set(rule) - {"constant", "offset"}:
            self.errors.append(f"{location}.exact_items has unknown properties")
        constant = rule.get("constant")
        if constant not in self.profile_constants:
            self.errors.append(
                f"{location}.exact_items references missing profile constant {constant!r}"
            )
            return
        offset = rule.get("offset", 0)
        if not isinstance(offset, int) or isinstance(offset, bool):
            self.errors.append(f"{location}.exact_items.offset must be an integer")
            return
        if self.profile_constants[constant] + offset < 0:
            self.errors.append(f"{location}.exact_items resolves below zero")

    def _validate_type(
        self, expression: TypeExpr, location: str, context_expression: bool
    ) -> None:
        if expression.name in {"list", "tuple"}:
            expected = 1 if expression.name == "list" else None
            if expected is not None and len(expression.args) != expected:
                self.errors.append(
                    f"{location} {expression.name} type must have {expected} argument"
                )
            if expression.name == "tuple" and not expression.args:
                self.errors.append(f"{location} tuple type must have at least one argument")
            for argument in expression.args:
                self._validate_type(argument, location, context_expression)
            return
        if expression.args:
            if expression.name == "CbcCmacEnvelope":
                if len(expression.args) != 1:
                    self.errors.append(
                        f"{location} CbcCmacEnvelope context must have one plaintext type"
                    )
                for argument in expression.args:
                    self._validate_type(argument, location, context_expression=True)
                return
            if expression.name not in self.schema_by_name:
                self.errors.append(f"{location} uses unsupported generic type {expression}")
                return
            dynamic_fields = self._dynamic_fields(self.schema_by_name[expression.name])
            if len(expression.args) != len(dynamic_fields):
                self.errors.append(
                    f"{location} supplies {len(expression.args)} context arguments to "
                    f"{expression.name}, expected {len(dynamic_fields)}"
                )
            for argument in expression.args:
                self._validate_type(argument, location, context_expression=True)
            return
        if expression.name not in self.primitive_by_name \
                and expression.name not in self.schema_by_name \
                and expression.name != "value":
            self.errors.append(f"{location} references missing type {expression.name}")

    def _validate_contexts(self) -> None:
        for name, rule in self.contexts.items():
            if not isinstance(rule, dict):
                self.errors.append(f"context rule {name} must be an object")
                continue
            semantic_role = rule.get("semantic_role")
            if semantic_role is not None and (
                not isinstance(semantic_role, str)
                or not NAME_PATTERN.fullmatch(semantic_role)
            ):
                self.errors.append(
                    f"context rule {name}.semantic_role must be a valid name"
                )
            variants = rule.get("variants")
            if variants is None:
                continue
            if not isinstance(variants, dict) or not variants:
                self.errors.append(f"context rule {name}.variants must be a nonempty object")
                continue
            for selector, value in variants.items():
                location = f"context rule {name} variant {selector!r}"
                if not isinstance(value, str):
                    self.errors.append(f"{location} must be a type string")
                    continue
                try:
                    expression = parse_type(value)
                except ValueError as error:
                    self.errors.append(f"{location} is invalid: {error}")
                    continue
                self._validate_type(expression, location, context_expression=True)

    def _validate_encryption_contexts(self) -> None:
        registry = self.encryption_contexts
        if registry.get("contexts_complete") is not True:
            self.errors.append("encryption_contexts.contexts_complete must be true")
        variants = registry.get("variants")
        if not isinstance(variants, dict) or not variants:
            self.errors.append("encryption_contexts.variants must be a nonempty object")
            return
        signed_variants = self.contexts.get("signed_message_content", {}).get(
            "variants", {}
        )
        for context, entry in variants.items():
            location = f"encryption context {context!r}"
            if not isinstance(entry, dict):
                self.errors.append(f"{location} must be an object")
                continue
            type_name = entry.get("type")
            if not isinstance(type_name, str):
                self.errors.append(f"{location}.type must be a type string")
                continue
            try:
                expression = parse_type(type_name)
            except ValueError as error:
                self.errors.append(f"{location}.type is invalid: {error}")
                continue
            self._validate_type(expression, location, context_expression=True)
            domain = entry.get("signature_domain")
            if domain is None:
                continue
            if not isinstance(domain, str):
                self.errors.append(f"{location}.signature_domain must be a string")
                continue
            if expression.name != "SignedMessage" or len(expression.args) != 1:
                self.errors.append(
                    f"{location}.signature_domain requires a SignedMessage<T> type"
                )
                continue
            expected_type = signed_variants.get(domain)
            if not isinstance(expected_type, str) or parse_type(expected_type) != expression.args[0]:
                self.errors.append(
                    f"{location}.signature_domain does not match the registered content type"
                )

    def _validate_cycles(self) -> None:
        graph: dict[str, set[str]] = {name: set() for name in self.schema_by_name}
        for schema in self.schemas:
            owner = schema.get("name")
            if owner not in graph:
                continue
            for field in schema.get("fields", []):
                type_name = field.get("type")
                if not isinstance(type_name, str):
                    continue
                try:
                    expression = parse_type(type_name)
                except ValueError:
                    continue
                graph[owner].update(self._schema_references(expression))

        active: list[str] = []
        visited: set[str] = set()

        def visit(name: str) -> None:
            if name in active:
                cycle = active[active.index(name) :] + [name]
                self.errors.append(f"schema cycle {' -> '.join(cycle)}")
                return
            if name in visited:
                return
            active.append(name)
            for target in sorted(graph[name]):
                visit(target)
            active.pop()
            visited.add(name)

        for name in graph:
            visit(name)

    def _schema_references(self, expression: TypeExpr) -> set[str]:
        references = set()
        if expression.name in self.schema_by_name:
            references.add(expression.name)
        for argument in expression.args:
            references.update(self._schema_references(argument))
        return references

    @staticmethod
    def _dynamic_fields(schema: dict[str, Any]) -> list[dict[str, Any]]:
        return [field for field in schema.get("fields", []) if field.get("type") == "value"]

    def _list_item_count(self, field: dict[str, Any], location: str) -> int | str:
        exact = field.get("exact_items")
        if isinstance(exact, dict):
            constant = exact["constant"]
            return self.profile_constants[constant] + exact.get("offset", 0)
        return f"{location}.max_items"

    def schema_max_size(self, schema: dict[str, Any]) -> int | None:
        return self._schema_max_size(schema, (), ())

    def _schema_max_size(
        self,
        schema: dict[str, Any],
        arguments: tuple[TypeExpr, ...],
        stack: tuple[str, ...],
    ) -> int | None:
        name = schema["name"]
        instance = str(TypeExpr(name, arguments))
        if instance in stack:
            raise CatalogError(
                f"context expansion cycle {' -> '.join((*stack, instance))}"
            )
        dynamic_fields = self._dynamic_fields(schema)
        substitutions = {
            field["name"]: argument
            for field, argument in zip(dynamic_fields, arguments)
        }
        total = self.container_by_name["struct"]["header_bytes"]
        total += self.container_by_name["struct"]["field_header_bytes"] * len(
            schema["fields"]
        )
        for field in schema["fields"]:
            expression = parse_type(field["type"])
            if expression.name == "value":
                size = self._value_max_size(
                    field,
                    substitutions.get(field["name"]),
                    (*stack, instance),
                )
            else:
                size = self._field_max_size(field, expression, (*stack, instance))
            if size is None:
                return None
            total += size
        return total

    def _field_max_size(
        self,
        field: dict[str, Any],
        expression: TypeExpr,
        stack: tuple[str, ...],
    ) -> int | None:
        if expression.name in self.primitive_by_name and not expression.args:
            primitive = self.primitive_by_name[expression.name]
            if "encoded_size" in primitive:
                return primitive["encoded_size"]
            return None
        if expression.name == "list":
            location = field["name"]
            count = self._list_item_count(field, location)
            item_size = self._type_max_size(expression.args[0], stack)
            if not isinstance(count, int) or item_size is None:
                return None
            return self.container_by_name["list"]["header_bytes"] + count * item_size
        return self._type_max_size(expression, stack)

    def _type_max_size(
        self, expression: TypeExpr, stack: tuple[str, ...]
    ) -> int | None:
        if expression.name in self.primitive_by_name and not expression.args:
            value = self.primitive_by_name[expression.name].get("encoded_size")
            return value if isinstance(value, int) else None
        if expression.name == "list":
            return None
        if expression.name == "tuple":
            sizes = [self._type_max_size(argument, stack) for argument in expression.args]
            if any(size is None for size in sizes):
                return None
            return self.container_by_name["tuple"]["header_bytes"] + sum(
                size for size in sizes if size is not None
            )
        if expression.name == "CbcCmacEnvelope" and len(expression.args) == 1:
            plaintext_size = self._type_max_size(expression.args[0], stack)
            if plaintext_size is None:
                return None
            ciphertext_size = (plaintext_size // 16 + 1) * 16
            return 56 + ciphertext_size
        if expression.name == "SignedMessage" and len(expression.args) == 1:
            content_size = self._type_max_size(expression.args[0], stack)
            if content_size is None:
                return None
            rule = self.contexts.get("signed_message_content", {})
            variants = rule.get("variants", {}) if isinstance(rule, dict) else {}
            matching_domains = [
                domain
                for domain, content_type in variants.items()
                if isinstance(content_type, str)
                and parse_type(content_type) == expression.args[0]
            ] if isinstance(variants, dict) else []
            if not matching_domains:
                return None
            domain_size = max(len(domain.encode("ascii")) for domain in matching_domains)
            return 119 + domain_size + content_size
        schema = self.schema_by_name[expression.name]
        return self._schema_max_size(schema, expression.args, stack)

    def _value_max_size(
        self,
        field: dict[str, Any],
        substitution: TypeExpr | None,
        stack: tuple[str, ...],
    ) -> int | None:
        if substitution is not None:
            return self._type_max_size(substitution, stack)
        rule = self.contexts[field["context_rule"]]
        variants = rule.get("variants")
        if not isinstance(variants, dict):
            return None
        sizes = [
            self._type_max_size(parse_type(value), stack)
            for value in sorted(set(variants.values()))
        ]
        if any(size is None for size in sizes):
            return None
        return max(size for size in sizes if size is not None)

    def schema_depth(self, schema: dict[str, Any]) -> DepthResult:
        return self._schema_depth(schema, (), ())

    def _schema_depth(
        self,
        schema: dict[str, Any],
        arguments: tuple[TypeExpr, ...],
        stack: tuple[str, ...],
    ) -> DepthResult:
        name = schema["name"]
        instance = str(TypeExpr(name, arguments))
        if instance in stack:
            raise CatalogError(
                f"context expansion cycle {' -> '.join((*stack, instance))}"
            )
        dynamic_fields = self._dynamic_fields(schema)
        substitutions = {
            field["name"]: argument
            for field, argument in zip(dynamic_fields, arguments)
        }
        best = DepthResult(0, ())
        unresolved: set[str] = set()
        for field in schema["fields"]:
            expression = parse_type(field["type"])
            if expression.name == "value":
                child = self._value_depth(
                    field,
                    substitutions.get(field["name"]),
                    (*stack, instance),
                )
            else:
                child = self._type_depth(expression, (*stack, instance))
            unresolved.update(child.unresolved_contexts)
            if child.depth > best.depth:
                label = f"{field['name']}:{child.path[0]}" if child.path else field["name"]
                best = DepthResult(child.depth, (label, *child.path[1:]))
        return DepthResult(
            1 + best.depth,
            (name, *best.path),
            frozenset(unresolved),
        )

    def _type_depth(self, expression: TypeExpr, stack: tuple[str, ...]) -> DepthResult:
        if expression.name in self.primitive_by_name and not expression.args:
            return DepthResult(0, ())
        if expression.name == "list":
            child = self._type_depth(expression.args[0], stack)
            return DepthResult(
                1 + child.depth,
                (str(expression), *child.path),
                child.unresolved_contexts,
            )
        if expression.name == "tuple":
            children = [self._type_depth(argument, stack) for argument in expression.args]
            child = max(children, key=lambda result: result.depth)
            unresolved = set().union(
                *(result.unresolved_contexts for result in children)
            )
            return DepthResult(
                1 + child.depth,
                (str(expression), *child.path),
                frozenset(unresolved),
            )
        if expression.name == "CbcCmacEnvelope" and len(expression.args) == 1:
            return DepthResult(1, (str(expression),))
        schema = self.schema_by_name[expression.name]
        return self._schema_depth(schema, expression.args, stack)

    def _value_depth(
        self,
        field: dict[str, Any],
        substitution: TypeExpr | None,
        stack: tuple[str, ...],
    ) -> DepthResult:
        rule_name = field["context_rule"]
        if substitution is not None:
            return self._type_depth(substitution, stack)
        rule = self.contexts[rule_name]
        variants = rule.get("variants")
        if not isinstance(variants, dict):
            return DepthResult(0, (), frozenset({rule_name}))
        results = [
            self._type_depth(parse_type(value), stack)
            for value in sorted(set(variants.values()))
        ]
        best = max(results, key=lambda result: result.depth)
        unresolved = set().union(*(result.unresolved_contexts for result in results))
        return DepthResult(best.depth, best.path, frozenset(unresolved))

    def unresolved_text_metadata(self) -> list[str]:
        result: list[str] = []
        unresolved = self.data.get("unresolved", {})
        if isinstance(unresolved, dict) and unresolved.get("text_encoder_non_nfc_input"):
            result.append("text_encoder_non_nfc_input")
        for schema in self.schemas:
            for field in schema["fields"]:
                if field.get("type") == "text" and field.get("text_profile") is None:
                    result.append(f"{schema['name']}.{field['name']}.text_profile")
        return result

    def unresolved_contexts(self) -> list[str]:
        result = []
        for schema in self.schemas:
            for field in schema["fields"]:
                if field.get("type") != "value":
                    continue
                rule_name = field["context_rule"]
                rule = self.contexts[rule_name]
                if not isinstance(rule.get("variants"), dict):
                    result.append(f"{schema['name']}.{field['name']} uses {rule_name}")
        return result

    def signed_contexts(
        self,
    ) -> list[tuple[str, TypeExpr, int | None, int | None, DepthResult]]:
        """Return the exact derivable metrics for every registered signature domain."""
        rule = self.contexts.get("signed_message_content", {})
        variants = rule.get("variants", {}) if isinstance(rule, dict) else {}
        result = []
        for domain, type_name in variants.items():
            expression = parse_type(type_name)
            content_size = self._type_max_size(expression, ())
            signed_size = (
                119 + len(domain.encode("ascii")) + content_size
                if content_size is not None
                else None
            )
            child = self._type_depth(expression, ())
            depth = DepthResult(
                1 + child.depth,
                ("SignedMessage", *child.path),
                child.unresolved_contexts,
            )
            result.append((domain, expression, content_size, signed_size, depth))
        return result

    def encryption_context_metrics(
        self,
    ) -> list[tuple[str, TypeExpr, int | None, int | None, int | None, DepthResult]]:
        """Return plaintext, ciphertext, envelope, and plaintext-depth metrics."""
        variants = self.encryption_contexts.get("variants", {})
        result = []
        for context, entry in variants.items():
            expression = parse_type(entry["type"])
            domain = entry.get("signature_domain")
            if isinstance(domain, str):
                content_size = self._type_max_size(expression.args[0], ())
                plaintext_size = (
                    119 + len(domain.encode("ascii")) + content_size
                    if content_size is not None
                    else None
                )
            else:
                plaintext_size = self._type_max_size(expression, ())
            ciphertext_size = (
                (plaintext_size // 16 + 1) * 16
                if plaintext_size is not None
                else None
            )
            envelope_size = (
                56 + ciphertext_size if ciphertext_size is not None else None
            )
            result.append(
                (
                    context,
                    expression,
                    plaintext_size,
                    ciphertext_size,
                    envelope_size,
                    self._type_depth(expression, ()),
                )
            )
        return result


def load_catalog(path: Path) -> Catalog:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise CatalogError(f"cannot read {path}: {error}") from error
    except json.JSONDecodeError as error:
        raise CatalogError(f"invalid JSON in {path}: {error}") from error
    if not isinstance(data, dict):
        raise CatalogError("catalog root must be an object")
    catalog = Catalog(path, data)
    catalog.validate()
    return catalog


def display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path.resolve())


def readable_wrap(value: str, subsequent_indent: str = "  ") -> str:
    return textwrap.fill(
        value,
        width=96,
        subsequent_indent=subsequent_indent,
        break_long_words=False,
        break_on_hyphens=False,
    )


def print_main_results(catalog: Catalog) -> None:
    field_count = sum(len(schema["fields"]) for schema in catalog.schemas)
    print("Summary")
    print(f"Catalog status {catalog.data.get('catalog_status', 'unspecified')}")
    print(f"Schemas {len(catalog.schemas)}")
    print(f"Fields {field_count}")

    print("\nStructural profile constants")
    for name, value in catalog.profile_constants.items():
        print(f"{name} {value}")

    print("\nDeterministic collection counts")
    for schema in catalog.schemas:
        for field in schema["fields"]:
            exact = field.get("exact_items")
            if not isinstance(exact, dict):
                continue
            location = f"{schema['name']}.{field['name']}"
            count = catalog._list_item_count(field, location)
            source = exact["constant"]
            offset = exact.get("offset", 0)
            derivation = source if offset == 0 else f"{source} {offset:+d}"
            print(f"{location} {count} items, from {derivation}")

    print("\nExact structural list sizes")
    list_header = catalog.container_by_name["list"]["header_bytes"]
    for schema in catalog.schemas:
        for field in schema["fields"]:
            expression = parse_type(field["type"])
            if expression.name != "list":
                continue
            location = f"{schema['name']}.{field['name']}"
            count = catalog._list_item_count(field, location)
            item_size = catalog._type_max_size(expression.args[0], ())
            if isinstance(count, int) and item_size is not None:
                value = f"exactly {list_header + count * item_size} bytes"
                print(readable_wrap(f"{location} {value}"))

    depths = [(schema, catalog.schema_depth(schema)) for schema in catalog.schemas]
    _, deepest = max(depths, key=lambda item: item[1].depth)
    print("\nKnown deepest nesting path")
    print("Depth counts open structs, lists, and tuples. Primitive values add no depth.")
    print("Generic context-selected values can increase a path until they are enumerated.")
    print(readable_wrap(f"{deepest.depth} containers  {' -> '.join(deepest.path)}"))

    print("\nSchema nesting paths")
    print("Each line gives the deepest path currently derivable from the catalog.")
    for schema, result in depths:
        suffix = ""
        if result.unresolved_contexts:
            suffix = f"  unresolved {', '.join(sorted(result.unresolved_contexts))}"
        print(readable_wrap(
            f"{schema['name']}  {result.depth}  {' -> '.join(result.path)}{suffix}"
        ))

    print("\nExact schema sizes")
    print("These values are fully determined by the catalog structure.")
    for schema in catalog.schemas:
        maximum = catalog.schema_max_size(schema)
        if maximum is not None:
            print(readable_wrap(f"{schema['name']} exactly {maximum} bytes"))

    print("\nRegistered signature-domain metrics")
    print("All signatures are fixed 64-byte Schnorr signatures encoded as bytes64 (65 bytes).")
    print("Sizes include the complete SignedMessage struct and its exact ASCII domain.")
    for domain, expression, content_size, signed_size, depth in catalog.signed_contexts():
        content_label = (
            f"content {content_size} bytes, signed {signed_size} bytes"
            if content_size is not None and signed_size is not None
            else "size OPEN"
        )
        depth_label = f"depth {depth.depth}"
        if depth.unresolved_contexts:
            depth_label += f" (unresolved {', '.join(sorted(depth.unresolved_contexts))})"
        print(readable_wrap(
            f"{domain} => {expression}; {content_label}; {depth_label}"
        ))

    print("\nRegistered CBC-CMAC encryption-context metrics")
    print("The registry is complete for canonical CBC-CMAC context labels in the protocol.")
    print("Ciphertext includes mandatory PKCS#7 padding; envelope includes all wire fields.")
    for context, expression, plaintext, ciphertext, envelope, depth in (
        catalog.encryption_context_metrics()
    ):
        size_label = (
            f"plaintext {plaintext} bytes, ciphertext {ciphertext} bytes, envelope {envelope} bytes"
            if plaintext is not None and ciphertext is not None and envelope is not None
            else "size OPEN"
        )
        print(readable_wrap(
            f"{context} => {expression}; {size_label}; plaintext depth {depth.depth}"
        ))

    contexts = catalog.unresolved_contexts()
    print(f"\nContext-dependent paths without enumerated variants {len(contexts)}")
    print("These generic value fields still need an exact type for every protocol context.")
    for item in contexts:
        print(item)

    text_metadata = catalog.unresolved_text_metadata()
    print(f"\nUnresolved text metadata {len(text_metadata)}")
    print("Entries below are missing required text-profile metadata.")
    for item in text_metadata:
        print(item)


def ascii_table(rows: list[list[str]], widths: list[int]) -> list[str]:
    border = "+" + "+".join("-" * (width + 2) for width in widths) + "+"
    output = [border]
    for cells in rows:
        wrapped = []
        for cell, width in zip(cells, widths):
            lines: list[str] = []
            for source_line in cell.splitlines() or [""]:
                lines.extend(
                    textwrap.wrap(
                        source_line,
                        width=width,
                        break_long_words=True,
                        break_on_hyphens=False,
                    )
                    or [""]
                )
            wrapped.append(lines)
        height = max(map(len, wrapped))
        for line_index in range(height):
            values = [
                lines[line_index] if line_index < len(lines) else ""
                for lines in wrapped
            ]
            output.append(
                "|" + "|".join(
                    f" {value:<{width}} " for value, width in zip(values, widths)
                ) + "|"
            )
        output.append(border)
    return output


def byte_count(value: int) -> str:
    unit = "byte" if value == 1 else "bytes"
    return f"{value} {unit}"


def context_value_details(catalog: Catalog, field: dict[str, Any]) -> list[str]:
    rule_name = field["context_rule"]
    rule = catalog.contexts[rule_name]
    details = [f"context rule {rule_name}"]
    selector = rule.get("selector")
    if isinstance(selector, str):
        details.append(f"selected by {selector}")
    semantic_role = rule.get("semantic_role")
    if isinstance(semantic_role, str):
        details.append(f"semantic role {semantic_role}")
    variants = rule.get("variants")
    if isinstance(variants, dict):
        details.extend(
            f"{context} => {value}"
            for context, value in variants.items()
        )
    return details


def primitive_layout(catalog: Catalog, primitive: dict[str, Any]) -> str:
    name = primitive["name"]
    if name == "bool":
        values = "; ".join(
            f"{value} [tag {tag}] {byte_count(primitive['encoded_size'])}"
            for value, tag in primitive["encodings"].items()
        )
        return f"{name} {values}"
    tag = primitive["tag"]
    if "payload_bytes" in primitive:
        payload_bytes = primitive["payload_bytes"]
        return (
            f"{name} [tag {tag}: 1 byte] [payload: {byte_count(payload_bytes)}] "
            f"total {byte_count(primitive['encoded_size'])}"
        )
    length_bytes = catalog.scalar_by_name[primitive["length_type"]]["encoded_size"]
    payload_properties = [primitive.get("encoding"), primitive.get("wire_normalization")]
    payload = " ".join(value for value in payload_properties if isinstance(value, str))
    payload = f"{payload} payload" if payload else "payload"
    return (
        f"{name} [tag {tag}: 1 byte] [length: {byte_count(length_bytes)}] "
        f"[{payload}: variable] total {primitive['header_bytes']} + payload bytes"
    )


def container_layout(catalog: Catalog, container: dict[str, Any]) -> str:
    name = container["name"]
    tag = container["tag"]
    if name in {"list", "tuple"}:
        count_bytes = catalog.scalar_by_name[container["count_type"]]["encoded_size"]
        return (
            f"{name} [tag {tag}: 1 byte] [count: {byte_count(count_bytes)}] "
            "[encoded items: variable]"
        )
    schema_id_bytes = catalog.scalar_by_name[container["schema_id_type"]]["encoded_size"]
    schema_version_bytes = catalog.scalar_by_name[
        container["schema_version_type"]
    ]["encoded_size"]
    field_count_bytes = catalog.scalar_by_name[
        container["field_count_type"]
    ]["encoded_size"]
    return (
        f"{name} [tag {tag}: 1 byte] [schema ID: {byte_count(schema_id_bytes)}] "
        f"[schema version: {byte_count(schema_version_bytes)}] "
        f"[field count: {byte_count(field_count_bytes)}] "
        f"[field ID: {byte_count(container['field_header_bytes'])}, encoded value] repeated"
    )


def schema_packet_layout(catalog: Catalog, schema: dict[str, Any]) -> list[str]:
    struct = catalog.container_by_name["struct"]
    schema_id_bytes = catalog.scalar_by_name[struct["schema_id_type"]]["encoded_size"]
    schema_version_bytes = catalog.scalar_by_name[
        struct["schema_version_type"]
    ]["encoded_size"]
    field_count_bytes = catalog.scalar_by_name[
        struct["field_count_type"]
    ]["encoded_size"]
    rows = [[
        f"tag {struct['tag']}\n1 byte",
        f"schema_id {schema['id']}\n{byte_count(schema_id_bytes)}",
        f"schema_version {schema['version']}\n{byte_count(schema_version_bytes)}",
        f"field_count {len(schema['fields'])}\n{byte_count(field_count_bytes)}",
    ]]
    output = ascii_table(rows, [14, 18, 22, 20])
    for field in schema["fields"]:
        expression = parse_type(field["type"])
        if expression.name == "value":
            value_size = catalog._value_max_size(field, None, ())
        else:
            value_size = catalog._field_max_size(field, expression, ())
        if value_size is not None:
            size = (
                f"value {value_size} bytes; field total "
                f"{struct['field_header_bytes'] + value_size} bytes"
            )
        elif expression.name in {"bytes", "text"}:
            header = catalog.primitive_by_name[expression.name]["header_bytes"]
            size = f"variable value; {header}-byte value header plus payload"
        elif expression.name == "list":
            size = "variable-length list value"
        elif expression.name == "value":
            size = "context-selected encoded value"
        else:
            size = "variable-length nested value"
        if expression.name == "value":
            size = "\n".join((size, *context_value_details(catalog, field)))
        field_rows = [[
            f"field_id {field['id']}\n{struct['field_header_bytes']} bytes",
            f"{field['name']}: {field['type']}\n{size}",
        ]]
        output.extend(ascii_table(field_rows, [16, 64])[1:])
    return output


def render_report(catalog: Catalog) -> str:
    output = io.StringIO()
    output.write("Boomerang wire catalog\n")
    output.write(
        "Generated from spec/wire_catalog.json by scripts/generate_wire_catalog.py.\n"
        "Do not edit by hand.\n\n"
    )
    with redirect_stdout(output):
        print_main_results(catalog)

    output.write("\nPrimitive wire layouts\n")
    output.write("Primitive totals include their canonical type tag.\n")
    for primitive in catalog.primitives:
        output.write(f"{readable_wrap(primitive_layout(catalog, primitive))}\n")

    output.write("\nContainer wire layouts\n")
    output.write("Container headers precede their recursively encoded contents.\n")
    for container in catalog.containers:
        output.write(f"{readable_wrap(container_layout(catalog, container))}\n")

    output.write("\nSchema packet layouts\n")
    output.write(
        "Frames show exact wire order and byte counts; display widths are not proportional.\n"
        "Every field begins with its field ID. Field totals include that ID.\n"
    )
    for schema in catalog.schemas:
        depth = catalog.schema_depth(schema)
        maximum = catalog.schema_max_size(schema)
        output.write(
            f"\nSchema {schema['name']}  ID {schema['id']}  version {schema['version']}\n"
        )
        output.write("\n".join(schema_packet_layout(catalog, schema)))
        output.write("\n")
        if maximum is not None:
            size_line = f"Exact encoded size  {maximum} bytes"
            output.write(readable_wrap(size_line))
            output.write("\n")
        if depth.unresolved_contexts:
            depth_label = "Known nesting lower bound"
        else:
            depth_label = "Deepest structural path"
        output.write(readable_wrap(
            f"{depth_label}  {depth.depth} containers  {' -> '.join(depth.path)}"
        ))
        output.write("\n")
        if depth.unresolved_contexts:
            output.write(
                "Unresolved contexts "
                f"{', '.join(sorted(depth.unresolved_contexts))}\n"
            )
    return output.getvalue()


def write_or_check_report(path: Path, content: str, check: bool) -> str:
    if check:
        try:
            existing = path.read_text(encoding="utf-8")
        except OSError as error:
            raise CatalogError(f"cannot read generated report {path}: {error}") from error
        if existing != content:
            raise CatalogError(
                f"generated report is stale: run {Path(__file__).name}"
            )
        return f"Generated report is current: {display_path(path)}"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    except OSError as error:
        raise CatalogError(f"cannot write generated report {path}: {error}") from error
    return f"Generated {display_path(path)}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Generate structural summaries and ASCII packet layouts from the "
            "wire catalog JSON."
        )
    )
    parser.add_argument(
        "catalog",
        nargs="?",
        type=Path,
        default=DEFAULT_CATALOG,
        help=f"catalog JSON path, default {DEFAULT_CATALOG}",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_REPORT,
        help=f"generated report path, default {DEFAULT_REPORT}",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail if the generated report does not match the output file",
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="also print the full generated report",
    )
    args = parser.parse_args(argv)
    try:
        catalog = load_catalog(args.catalog.resolve())
        report = render_report(catalog)
        result = write_or_check_report(args.output.resolve(), report, args.check)
        print(result)
        if args.stdout:
            print(report, end="")
    except CatalogError as error:
        print(f"Catalog generation failed\n{error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Validate the canonical wire catalog and report its derived structure."""

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
DEFAULT_REPORT = ROOT / "spec" / "wire_catalog_report.txt"
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
        contexts = data.get("context_rules", {})
        if not isinstance(contexts, dict):
            self.errors.append("context_rules must be an object")
            contexts = {}
        self.contexts: dict[str, Any] = contexts
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
        self._validate_cycles()
        if self.errors:
            raise CatalogError("\n".join(f"- {error}" for error in self.errors))

    def _validate_top_level(self) -> None:
        if self.data.get("catalog_format_version") != 1:
            self.errors.append("catalog_format_version must be 1")
        invariants = self.data.get("invariants")
        if not isinstance(invariants, dict):
            self.errors.append("invariants must be an object")
            return
        fields = [
            field
            for schema in self.schemas
            if isinstance(schema.get("fields"), list)
            for field in schema["fields"]
            if isinstance(field, dict)
        ]
        expected_counts = {
            "schema_count": len(self.schemas),
            "field_count": len(fields),
            "text_field_count": sum(field.get("type") == "text" for field in fields),
            "variable_bytes_field_count": sum(
                field.get("type") == "bytes" for field in fields
            ),
            "list_field_count": sum(
                isinstance(field.get("type"), str)
                and field["type"].startswith("list<")
                for field in fields
            ),
            "dynamic_value_field_count": sum(
                field.get("type") == "value" for field in fields
            ),
        }
        for name, expected in expected_counts.items():
            if invariants.get(name) != expected:
                self.errors.append(
                    f"invariants.{name} is {invariants.get(name)!r}, expected {expected}"
                )
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
            self._validate_optional_positive(schema, "max_encoded_size", name)
            self._validate_optional_positive(schema, "max_nesting_depth", name)
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

    def _validate_optional_positive(
        self, record: dict[str, Any], key: str, location: str
    ) -> None:
        value = record.get(key)
        if value is not None and not self._is_positive_integer(value):
            self.errors.append(f"{location}.{key} must be null or a positive integer")

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
        if expression.name in {"bytes", "text"} and not expression.args:
            self._validate_optional_nonnegative(field, "max_payload_bytes", location)
        if expression.name == "text" and "text_profile" not in field:
            self.errors.append(f"{location}.text_profile is missing")
        if expression.name == "list":
            self._validate_optional_nonnegative(field, "max_items", location)

    def _validate_optional_nonnegative(
        self, record: dict[str, Any], key: str, location: str
    ) -> None:
        if key not in record:
            self.errors.append(f"{location}.{key} is missing")
            return
        value = record[key]
        if value is not None and (
            not isinstance(value, int) or isinstance(value, bool) or value < 0
        ):
            self.errors.append(f"{location}.{key} must be null or a nonnegative integer")

    def _validate_type(
        self, expression: TypeExpr, location: str, context_expression: bool
    ) -> None:
        if expression.name == "list":
            if len(expression.args) != 1:
                self.errors.append(f"{location} list type must have one argument")
            for argument in expression.args:
                self._validate_type(argument, location, context_expression)
            return
        if expression.args:
            if not context_expression or expression.name not in self.schema_by_name:
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
                if expression == TypeExpr("value"):
                    rule = self.contexts.get(field.get("context_rule"), {})
                    variants = rule.get("variants", {}) if isinstance(rule, dict) else {}
                    if isinstance(variants, dict):
                        for value in variants.values():
                            if isinstance(value, str):
                                try:
                                    graph[owner].update(
                                        self._schema_references(parse_type(value))
                                    )
                                except ValueError:
                                    pass

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

    def schema_formula(self, schema: dict[str, Any]) -> str:
        fields = schema["fields"]
        fixed = self.container_by_name["struct"]["header_bytes"]
        fixed += self.container_by_name["struct"]["field_header_bytes"] * len(fields)
        terms: list[str] = []
        for field in fields:
            part = self._field_formula(schema, field)
            if isinstance(part, int):
                fixed += part
            else:
                terms.append(part)
        return " + ".join([str(fixed), *terms])

    def _field_formula(self, schema: dict[str, Any], field: dict[str, Any]) -> int | str:
        expression = parse_type(field["type"])
        location = f"{schema['name']}.{field['name']}"
        if expression.name in self.primitive_by_name and not expression.args:
            primitive = self.primitive_by_name[expression.name]
            if "encoded_size" in primitive:
                return primitive["encoded_size"]
            return f"({primitive['header_bytes']} + {location}.max_payload_bytes)"
        if expression.name == "list":
            item = self._type_formula(expression.args[0])
            return f"({self.container_by_name['list']['header_bytes']} + {location}.max_items * ({item}))"
        if expression.name == "value":
            return self._context_formula(field["context_rule"])
        return f"max_size({expression})"

    def _type_formula(self, expression: TypeExpr) -> str:
        if expression.name in self.primitive_by_name and not expression.args:
            primitive = self.primitive_by_name[expression.name]
            if "encoded_size" in primitive:
                return str(primitive["encoded_size"])
            return f"max_size({expression})"
        if expression.name == "list":
            return f"max_size({expression})"
        return f"max_size({expression})"

    def _context_formula(self, rule_name: str) -> str:
        rule = self.contexts[rule_name]
        variants = rule.get("variants")
        if not isinstance(variants, dict):
            return f"max_size(context({rule_name}))"
        values = sorted(set(variants.values()))
        terms = [f"max_size({value})" for value in values]
        if len(terms) == 1:
            return terms[0]
        return f"max({', '.join(terms)})"

    def schema_depth(self, schema: dict[str, Any]) -> DepthResult:
        return self._schema_depth(schema, (), ())

    def _schema_depth(
        self,
        schema: dict[str, Any],
        arguments: tuple[TypeExpr, ...],
        stack: tuple[str, ...],
    ) -> DepthResult:
        name = schema["name"]
        if name in stack:
            raise CatalogError(f"context expansion cycle {' -> '.join((*stack, name))}")
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
                    (*stack, name),
                )
            else:
                child = self._type_depth(expression, (*stack, name))
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

    def unresolved_bounds(self) -> list[str]:
        result: list[str] = []
        unresolved = self.data.get("unresolved", {})
        if isinstance(unresolved, dict):
            if unresolved.get("global_nesting_depth") is None:
                result.append("global_nesting_depth")
            if unresolved.get("top_level_object_limits") is None:
                result.append("top_level_object_limits")
        for schema in self.schemas:
            name = schema["name"]
            if schema.get("max_encoded_size") is None:
                result.append(f"{name}.max_encoded_size")
            if schema.get("max_nesting_depth") is None:
                result.append(f"{name}.max_nesting_depth")
            for field in schema["fields"]:
                location = f"{name}.{field['name']}"
                expression = parse_type(field["type"])
                if expression.name in {"bytes", "text"} and field.get("max_payload_bytes") is None:
                    result.append(f"{location}.max_payload_bytes")
                if expression.name == "list" and field.get("max_items") is None:
                    result.append(f"{location}.max_items")
                    result.append(f"{location}.max_encoded_size derived from item and element bounds")
        return result

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


def print_main_results(catalog: Catalog) -> None:
    field_count = sum(len(schema["fields"]) for schema in catalog.schemas)
    print("Validation passed")
    print(f"Source {display_path(catalog.source)}")
    print(f"Schemas {len(catalog.schemas)}")
    print(f"Fields {field_count}")

    depths = [(schema, catalog.schema_depth(schema)) for schema in catalog.schemas]
    deepest_schema, deepest = max(depths, key=lambda item: item[1].depth)
    print("\nKnown deepest nesting path")
    print(f"{deepest.depth} containers  {' -> '.join(deepest.path)}")

    print("\nSchema nesting paths")
    for schema, result in depths:
        suffix = ""
        if result.unresolved_contexts:
            suffix = f"  unresolved {', '.join(sorted(result.unresolved_contexts))}"
        print(f"{schema['name']}  {result.depth}  {' -> '.join(result.path)}{suffix}")

    print("\nSymbolic maximum-size formulas")
    for schema in catalog.schemas:
        print(f"{schema['name']} = {catalog.schema_formula(schema)}")

    contexts = catalog.unresolved_contexts()
    print(f"\nContext-dependent paths without enumerated variants {len(contexts)}")
    for item in contexts:
        print(item)

    text_metadata = catalog.unresolved_text_metadata()
    print(f"\nUnresolved text metadata {len(text_metadata)}")
    for item in text_metadata:
        print(item)

    bounds = catalog.unresolved_bounds()
    print(f"\nUnresolved bounds {len(bounds)}")
    for item in bounds:
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


def primitive_layout(primitive: dict[str, Any]) -> str:
    name = primitive["name"]
    if name == "bool":
        return "bool false [tag 0x01] 1 byte; true [tag 0x02] 1 byte"
    tag = primitive["tag"]
    if "payload_bytes" in primitive:
        return (
            f"{name} [tag {tag}: 1 byte] [payload: {primitive['payload_bytes']} bytes] "
            f"total {primitive['encoded_size']} bytes"
        )
    payload = "UTF-8 NFC payload" if name == "text" else "payload"
    return (
        f"{name} [tag {tag}: 1 byte] [length: 4 bytes] [{payload}: variable] "
        f"total {primitive['header_bytes']} + payload bytes"
    )


def container_layout(container: dict[str, Any]) -> str:
    name = container["name"]
    tag = container["tag"]
    if name == "list":
        return "list [tag 0x30: 1 byte] [count: 4 bytes] [encoded items: variable]"
    if name == "tuple":
        return "tuple [tag 0x31: 1 byte] [count: 2 bytes] [encoded items: variable]"
    return (
        f"struct [tag {tag}: 1 byte] [schema ID: 2 bytes] "
        "[schema version: 2 bytes] [field count: 2 bytes] "
        "[field ID: 2 bytes, encoded value] repeated"
    )


def schema_packet_layout(catalog: Catalog, schema: dict[str, Any]) -> list[str]:
    struct = catalog.container_by_name["struct"]
    rows = [[
        "tag 0x40\n1 byte",
        f"schema_id {schema['id']}\n2 bytes",
        f"schema_version {schema['version']}\n2 bytes",
        f"field_count {len(schema['fields'])}\n2 bytes",
    ]]
    output = ascii_table(rows, [14, 18, 22, 20])
    for field in schema["fields"]:
        value_size = catalog._field_formula(schema, field)
        if isinstance(value_size, int):
            size = (
                f"value {value_size} bytes; field total "
                f"{struct['field_header_bytes'] + value_size} bytes"
            )
        else:
            size = (
                f"value {value_size}; field total "
                f"{struct['field_header_bytes']} + {value_size}"
            )
        field_rows = [[
            f"field_id {field['id']}\n{struct['field_header_bytes']} bytes",
            f"{field['name']}: {field['type']}\n{size}",
        ]]
        output.extend(ascii_table(field_rows, [16, 64])[1:])
    return output


def render_report(catalog: Catalog) -> str:
    output = io.StringIO()
    output.write("Boomerang canonical wire catalog report\n")
    output.write("Generated by scripts/generate_wire_catalog.py\n\n")
    with redirect_stdout(output):
        print_main_results(catalog)

    output.write("\nPrimitive wire layouts\n")
    for primitive in catalog.primitives:
        output.write(f"{primitive_layout(primitive)}\n")

    output.write("\nContainer wire layouts\n")
    for container in catalog.containers:
        output.write(f"{container_layout(container)}\n")

    output.write("\nSchema packet layouts\n")
    output.write(
        "Frames show exact wire order and byte counts; display widths are not proportional.\n"
        "Every field begins with its two-byte field ID. Field totals include that ID.\n"
    )
    for schema in catalog.schemas:
        depth = catalog.schema_depth(schema)
        output.write(
            f"\nSchema {schema['name']}  ID {schema['id']}  version {schema['version']}\n"
        )
        output.write("\n".join(schema_packet_layout(catalog, schema)))
        output.write(f"\nMaximum size formula {catalog.schema_formula(schema)}\n")
        output.write(
            f"Known nesting {depth.depth} containers  {' -> '.join(depth.path)}\n"
        )
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
        return f"Verified {display_path(path)}"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    except OSError as error:
        raise CatalogError(f"cannot write generated report {path}: {error}") from error
    return f"Wrote {display_path(path)}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate the wire catalog and generate formulas, nesting paths, "
            "unresolved limits, and ASCII packet layouts."
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
        print(f"Catalog validation failed\n{error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

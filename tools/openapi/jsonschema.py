import logging
import re

from genson import SchemaBuilder
from genson.schema.strategies import (
    Boolean,
    List,
    Null,
    Number,
    Object,
    String,
    Tuple,
)

log = logging.getLogger(__name__)


class NullAsString(Null):
    """
    Treats null values as nullable strings in the generated schema.
    """

    JS_TYPE = "string"
    PYTHON_TYPE = type(None)

    def to_schema(self):
        schema = super().to_schema()
        schema["type"] = self.JS_TYPE
        schema["nullable"] = True
        return schema


class ConstrainedList(List):
    def to_schema(self):
        schema = super().to_schema()
        schema["minItems"] = 0
        schema["maxItems"] = 100
        if "items" not in schema:
            schema["items"] = {}
        return schema


VARIABLE_NAME_PATTERN = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]{0,32}$")


class SafeObject(Object):
    """
    Remove all properties that:
    - match /^@/ (e.g., @type, @id)
    - do not match /^[a-zA-Z][a-zA-Z0-9_]+$/ (i.e., are not simple field names)
    """

    def add_object(self, obj):
        properties = set()
        for prop, subobj in obj.items():
            #
            # Skip properties that do not match with
            #   allowed variable name patters.
            #
            if not VARIABLE_NAME_PATTERN.match(prop):
                log.warning(
                    f"Skipping property '{prop}' that does not match variable name pattern"
                )
                continue

            pattern = None

            if prop not in self._properties:
                pattern = self._matching_pattern(prop)

            if pattern is not None:
                self._pattern_properties[pattern].add_object(subobj)
            else:
                properties.add(prop)
                self._properties[prop].add_object(subobj)

        if self._required is None:
            self._required = properties
        else:
            self._required &= properties


class OAS3SchemaBuilder(SchemaBuilder):
    STRATEGIES = (
        NullAsString,
        Boolean,
        Number,
        String,
        ConstrainedList,
        Tuple,
        SafeObject,
    )

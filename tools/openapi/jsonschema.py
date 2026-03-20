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


class OAS3SchemaBuilder(SchemaBuilder):
    STRATEGIES = (
        NullAsString,
        Boolean,
        Number,
        String,
        List,
        Tuple,
        Object,
    )

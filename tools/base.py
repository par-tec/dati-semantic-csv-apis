from typing import TypedDict

JsonLD = TypedDict("JsonLD", {"@context": dict, "@graph": list}, total=False)
JsonLDFrame = TypedDict("JsonLDFrame", {"@context": dict}, total=False)
TEXT_TURTLE = "text/turtle"
OX_TURTLE = "ox-turtle"
APPLICATION_LD_JSON = "application/ld+json"

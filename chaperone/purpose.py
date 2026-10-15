from .policy import MINIMISABLE, current


# does this purpose need this kind of identifier? undeclared purposes need everything
def omits(purpose: str, label: str) -> bool:
    p = current().purposes.get(purpose)
    return p is not None and label in MINIMISABLE and label in p["omit"]


# finishes the sentence "Not needed to ..."
def task(purpose: str) -> str:
    p = current().purposes.get(purpose)
    return p["task"] if p else purpose

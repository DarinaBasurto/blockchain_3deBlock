from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..block import Block


class Consensus(ABC):
    """Interfaz que todo mecanismo de consenso debe cumplir."""

    @abstractmethod
    def prepare_block(self, block: "Block",
                      chain: list["Block"]) -> "Block":
        """Ajusta el bloque antes de proponerlo (minar, firmar, etc.)."""
        ...

    @abstractmethod
    def validate_block(self, block: "Block",
                       chain: list["Block"]) -> bool:
        """Valida un bloque contra las reglas del mecanismo y la cadena."""
        ...

    @abstractmethod
    def select_chain(self,
                     candidates: list[list["Block"]]) -> list["Block"]:
        """Elige la cadena canónica entre varias (fork)."""
        ...
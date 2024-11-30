from dataclasses import dataclass

@dataclass
class QasmCircuit():
    """
    A dataclass for storing basic data to return data of one execution for inputs in OpenQasm"""
    circuit=None
    name=None
    metadata={}

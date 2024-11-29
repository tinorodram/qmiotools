from qiskit.pulse import Schedule
from qiskit.version import get_version_info
from .qpbuilder import QPBuilder
from ...version import VERSION
import warnings
import logging
import io

logger=logging.getLogger("OPExporter/%s"%VERSION)
 
class OPExporter:
    """OpenPulse exporter main class."""
    def __init__(self, logging_level: int=logging.NOTSET):
        logger.setLevel(logging_level)
        qiskitversion= get_version_info().split(".")
        if int(qiskitversion[0])>=2:
            warnings.Warning("Qiskit version %s could not be compatible with Schedule")
            
    def dumps(self, Schedule):
        """Convert the schedule to OpenPulse, returning the result as a string."""

        with io.StringIO() as stream:
            self.dump(Schedule, stream)
            return stream.getvalue()
    
    def dump(self, Schedule, program):
        """Convert the schedule to OpenPulse, dumping the result to a file or text stream."""
        builder = QPBuilder(logging_level=logger.level)
        sentences=builder.build_program(Schedule)
        head=builder.build_header()
        program.write(head)

        for piece in sentences:
            program.write(piece+'\n')

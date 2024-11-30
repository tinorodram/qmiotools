from qiskit.pulse import Schedule, ScheduleBlock
from qiskit.version import get_version_info
from typing import Union
from .qpbuilder import QPBuilder
from ...version import VERSION
import warnings
import logging
import io

logger=logging.getLogger("OPExporter/%s"%VERSION)
 
class OPExporter:
    """
    OpenPulse exporter main class.
    
    Args:
            logging_level (int): flag to indicate the logging level. Better if use the :py:mod:`logging` package levels. Default :py:data:`logging.NOTSET`
    """
    
    def __init__(self, logging_level: int=logging.NOTSET):
        logger.setLevel(logging_level)
        qiskitversion= get_version_info().split(".")
        if int(qiskitversion[0])>=2:
            warnings.Warning("Qiskit version %s could not be compatible with Schedule")
            
    def dumps(self, schedule:  Union[Schedule,ScheduleBlock]):
        """
        Convert the schedule to `OpenPulse <https://openqasm.com/language/openpulse.html>`_, returning the result as a string.
        
        Args:
            schedule (Schedule or ScheduleBlock): a valid :py:class:`qiskit.pulse.Schedule` to translate to OpenPulse grammar.
        
        Returns:
            str: a string with the OpenPulse program
        
        Raised:
            :py:class:`ValueError`: if an invalid :py:class:`qiskit.pulse.Schedule` was passed as arguments
        
        """
        if not isinstance(schedule,Schedule) and not isinstance(schedule,ScheduleBlock):
            raise ValueError("schedule must be a valid Qiskit Schedule or ScheduleBlock")
            
        with io.StringIO() as stream:
            self.dump(schedule, stream)
            return stream.getvalue()
    
    def dump(self, schedule: Union[Schedule,ScheduleBlock], program: io.IOBase):
        """
        
        Convert the schedule to `OpenPulse <https://openqasm.com/language/openpulse.html>`_, dumping the result to a stream.
        
        """
        
        if not isinstance(schedule,Schedule) and not isinstance(schedule,ScheduleBlock):
            raise ValueError("schedule must be a valid Qiskit Schedule")
        
        if not isinstance(program,io.IOBase):
            raise ValueError("program must be a valid IO stream")
            
        builder = QPBuilder(logging_level=logger.level)
        sentences=builder.build_program(schedule)
        head=builder.build_header()
        program.write(head)

        for piece in sentences:
            program.write(piece+'\n')

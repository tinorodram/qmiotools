from qiskit.providers import BackendV2
from qiskit.providers import JobStatus, JobV1  
from qiskit.result import Result

from ...version import VERSION

from typing import Optional, Any
import logging


class QmioJob(JobV1):
    """

    A class to return the results of a Job following the structure of :py:class:`qiskit.providers.JobV1`"""

    def __init__(
        self,
        backend: Optional[BackendV2],
        job_id: str,
        jobstatus: JobStatus = JobStatus.INITIALIZING,
        result: Result = None,
        **kwargs 
    ):
        """Initializes the synchronous job."""

        super().__init__(backend, job_id, **kwargs)
        self._jobstatus=jobstatus
        self._result=result
        self.version=VERSION
        
    def submit(self) -> None:
        """
        
        This method is not necessary for this backend, because currently the execution is synchronous


        """
        raise NotImplemented("Not necessary for this backend")

    def result(self) -> Result:   
        return self._result
        
        

    def cancel(self) -> None:
        """
        This method is not necessary for this backend, because currently the execution is synchronous
        """
        raise NotImplemented("Not necessary for this backend")

    def status(self) -> Any:
        return self._jobstatus

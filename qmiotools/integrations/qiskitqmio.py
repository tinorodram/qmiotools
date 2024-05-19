from qiskit.providers import QubitProperties, BackendV2, Provider, Options, Job
from qiskit.providers import JobStatus, JobV1  
from qiskit.providers.models.backendstatus import BackendStatus

from qiskit.circuit.gate import Instruction
from qiskit.circuit.library import ECRGate, IGate, Measure, RZXGate, RZGate, SXGate,ECRGate
from qiskit.circuit import Delay
from qiskit.transpiler import Target, InstructionProperties
from qiskit.circuit.library import UGate, CXGate, Measure
from qiskit.circuit import Parameter, QuantumCircuit
from qiskit.pulse import Schedule
from qiskit.result.models import ExperimentResult, ExperimentResultData
from qiskit.result import Result, Counts  
from qiskit.qobj import QobjExperimentHeader
from qiskit import qasm3
from qiskit.qobj.utils import MeasLevel

import math
import uuid
#import datetime
from collections import Counter, OrderedDict
from datetime import date
from typing import Union, List, Optional, Dict,  Any, TYPE_CHECKING, Union, cast
from dataclasses import dataclass
import warnings

from ..exceptions import QPUException, QmioException
from .utils import import_last_calibration
from ..version import VERSION


from qmio import QmioRuntimeService


QUBIT_POSITIONS=[(1,2),(1,3),(1,4),(1,5),(1,6),
            (2,6.5),(2,4.5),(2,2.5),
            (3,1),(3,2),(3,3),(3,4),(3,5),
            (4,5.5),(4,3.5),(4,1.5),
            (5,1),(5,2),(5,3),(5,4),(5,5),(5,6),
            (6,6.5),(6,4.5),(6,2.5),(6,1),
            (7,1),(7,2),(7,3),(7,4),(7,5),(7,6)]



class QmioJob(JobV1):
    """
    :py:class:`qiskit.providers.JobV1`"""

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
        raise NotImplemented("Not necessary for this backend")

    def result(self) -> Result:   
        return self._result
        
        

    def cancel(self) -> None:
        raise NotImplemented("Not necessary for this backend")

    def status(self) -> Any:
        return self._jobstatus

@dataclass
class QasmCircuit():
    """
    A dataclass for storing basic data to return data of one execution"""
    circuit=None
    name=None







DEFAULT_OPTIONS=Options(shots=8192,memory=False,repetition_period=250e-6)

class QmioBackend(BackendV2):
    """
    Backend to execute Jobs in Qmio QPU. 
    
    It uses :py:class:`qmio.QmioRuntimeService` to submit circuits to the QPU. By default, the calibrations are read from the last JSON file in the directory set by environ variable QMIO_CALIBRATIONS, but accepts a direct filename to use instead of.
    
    The execution using the method run is synchronous.
    
    To create a new backend use:
    
        backend=QmioBackend()
    
    It will print the file where the calibration were read in. If you want to use a specific calibrations file, use:
        
            backend=QmioBackend(<file name>)
    
   
    """
 

    def __init__(self, calibration_file: str=None, **kwargs):
        
        self._provider=None
        self._name="Qmio"
        self._description="CESGA Qmio"
        self._backend_version=VERSION
        super().__init__(self, **kwargs)
        
        
        calibrations=import_last_calibration(calibration_file)
        properties=[]
        qubits=calibrations.get_qubits()
        
        #
        # Load Qubits Properties
        #
        for i in qubits:
            properties.append(QubitProperties(t1=qubits[i]["T1"]*1e-6,t2=qubits[i]["T2e"]*1e-6,frequency=qubits[i]["Drive Frequency "]))
        
        target = Target(description="qmio", num_qubits=len(properties), dt=0.5*1e-9, granularity=1, 
                        min_length=1, pulse_alignment=1, acquire_alignment=1, 
                        qubit_properties=properties, concurrent_measurements=None)
        
        
        theta = Parameter('theta')
        
        errors=calibrations.get_1Q_errors()
        durations=calibrations.get_1Q_durations()
        sx_inst=OrderedDict()
        
        for i in errors:
            sx_inst[i]=InstructionProperties(duration=durations[i], error=errors[i])
        
        
        target.add_instruction(SXGate(), sx_inst)
        
        rz_inst=OrderedDict()
        for i in durations:
            rz_inst[i]=InstructionProperties(duration=0.0)
        target.add_instruction(RZGate(theta), rz_inst)
        
        #q2_inst=calibrations.get_2Q_errors()
        #target.add_instruction(ECRGate(), q2_inst)   
        errors=calibrations.get_2Q_errors()
        durations=calibrations.get_2Q_durations()
        #print(durations)
        ecr_inst=OrderedDict()
        for i in errors:
            ecr_inst[i]=InstructionProperties(duration=durations[i], error=errors[i])
            #print(i,ecr_inst[i])
        
        target.add_instruction(ECRGate(), ecr_inst)
        #target.add_instruction(RZXGate(math.pi/4), ecr_inst, name="rzx(pi/4)")
        
        measures=OrderedDict()
        for i in qubits:
            measures[(int(i[2:-1]),)]=InstructionProperties(error=1.0-qubits[i]["Fidelity readout"],duration=qubits[i]["Measuring time"]*1e-6)
        
        target.add_instruction(Measure(),measures)
        
        delays=OrderedDict()
        for i in qubits:
            delays[(int(i[2:-1]),)]=None
        
        target.add_instruction(Delay(Parameter("t")),measures)
                               
        self._target = target
        
        self._options = DEFAULT_OPTIONS
        self._version = VERSION
        self._max_circuits=1000
        self._max_shots=8192
        self.max_shots=self._max_circuits*self._max_shots
        

    @property
    def target(self) -> Target:
        return self._target
    
    @classmethod
    def _default_options(cls):
        return DEFAULT_OPTIONS
    
    @property
    def max_circuits(self):
        return self._max_circuits
    
    def run(self, run_input: Union[Union[QuantumCircuit,Schedule, str],List[Union[QuantumCircuit,Schedule,str]]], **options) -> QmioJob:
        """Run on QMIO QPU. This method is Synchronous, so it will wait for the results from the QPU

        Args:
            run_input (QuantumCircuit or Schedule or Str - a QASM string - or list): An
                individual or a list of :class:`.QuantumCircuit`,
                or :class:`~qiskit.pulse.Schedule` or a string with a QASM 3.0 objects to
                run on the backend.
            options: Any kwarg options to pass to the backend for running the
                config. If a key is also present in the options
                attribute/object then the expectation is that the value
                specified will be used instead of what's set in the options
                object.

        Returns:
            Job: The job object for the run
        
        Raises:
            QPUException if there is one error in the QPU
            QmioException if there are errors in the input parameters.
        """

        if isinstance(options,Options):
            shots=options.get("shots",default=self._options.get("shots"))
            memory=options.get("memory",default=self._options.get("shots"))
            repetition_period=options.get("repetition_period",default=self._options.get("repetition_period"))
        else:
            if "shots" in options:
                shots=options["shots"]
            else:
                shots=self._options.get("shots")

            if "memory" in options:
                shots=options["memory"]
            else:
                memory=self._options.get("memory")

            if "repetition_period" in options:
                repetition_period=options["repetition_period"]
            else:
                repetition_period=self._options.get("repetition_period")


        if isinstance(run_input,str) and not "OPENQASM" in run_input:
            raise QmioException("Input seems not to be a valid OPENQASM 3.0 file...")
        
        if isinstance(run_input,QuantumCircuit) or isinstance(run_input,Schedule) or isinstance(run_input,str):
            circuits=[run_input]
        else:
            circuits=run_input

        if shots*len(circuits) > self.max_shots:
            raise QmioException("Total number of shots %d larger than capacity %d"%(shots,self.max_shots))
        

        service = QmioRuntimeService()
        #print(service)
        job_id=uuid.uuid4()
        ExpResult=[]
        with service.backend(name="qpu") as backend:
            for c in circuits:
                if isinstance(c,QuantumCircuit) or isinstance(c,Schedule):
                    qasm=qasm3.dumps(c, basis_gates=self.operation_names).replace("\n","")
                    print(qasm)
                else:
                    qasm=c
                remain_shots=shots
                ExpDict={}
              
                warning_raised = False
                while (remain_shots > 0):
                    try:
                        results = backend.run(circuit=qasm, shots=min(self._max_shots,remain_shots),repetition_period=repetition_period)
                    except TypeError:
                        if not warning_raised:
                            warnings.warn("No repetition_period allowed")
                            warning_raised=True
                        results = backend.run(circuit=qasm, shots=min(self._max_shots,remain_shots))
                        
                    #print("Results:",results)
                    if "Exception" in results:
                        raise QPUException(results["Exception"])
                    try:
                        r=results["results"][list(results["results"].keys())[0]]
                    except:
                        raise QPUException("QPU does not return results")
                    for k in r:
                        if not memory:
                            key=hex(int(k[::-1],base=2))
                            ExpDict[key]=ExpDict[key]+r[k] if key in ExpDict else r[k]
                        else:
                            raise QmioException("Binary for the next version")
                    remain_shots=remain_shots-self._max_shots
                metadata=None
                
                if "execution_metrics" in results:
                    metadata=results["execution_metrics"] 
               
                if isinstance(c,str):
                    c_copy=c
                    c=QasmCircuit()
                    c.circuit=c_copy
                    c.name="QASM"
                    print(c)

                dd={
                    'shots': shots,
                    'success': True,
                    'data': {

                        'counts': ExpDict,
                        'metadata': None,
                    },
                    'header': {'name': c.name},

                    }
                ExpResult.append(dd)

        result_dict = {
            'backend_name': self._name,
            'backend_version': self._version,
            'qobj_id': None,
            'job_id': job_id,
            'success': True,
            'results': ExpResult,
            'date': date.today().isoformat(),

        }

        results=Result.from_dict(result_dict)

        job=QmioJob(backend=self,job_id=uuid.uuid4(), jobstatus=JobStatus.DONE, result=results)
        
        return job

from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel

def FakeQmio(calibration_file: str=None, thermal_relaxation: bool = True, temperature: float = 0 , gate_error: bool=False, readout_error: bool=False, **kwargs) -> AerSimulator:
    qmio=QmioBackend(calibration_file)
    noise_model = NoiseModel.from_backend(
        qmio, thermal_relaxation=thermal_relaxation,
        temperature=temperature,
        gate_error=gate_error,
        readout_error=readout_error)

    cls= AerSimulator.from_backend(qmio, noise_model=noise_model, **kwargs)
    cls.name = "FakeQmio"
    cls.description ="Fake backend for Qmio that uses the last calibrations and AerSimulator"
    return cls
        
    
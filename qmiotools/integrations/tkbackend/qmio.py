import pytket
from pytket import Circuit
from pytket.qasm import circuit_from_qasm_str,circuit_from_qasm, circuit_to_qasm, circuit_to_qasm_str
from pytket.backends import Backend
from pytket.backends.backendinfo import BackendInfo
from typing import List
from pytket.passes import RebaseCustom, SquashCustom
from pytket.architecture import Architecture, RingArch
from pytket.circuit import OpType
from pytket.backends import ResultHandle, CircuitStatus, StatusEnum, CircuitNotRunError
from pytket.backends.resulthandle import _ResultIdTuple
from pytket.backends.backendresult import BackendResult, OutcomeArray
from pytket.placement import GraphPlacement, NoiseAwarePlacement
from pytket.transform import Transform
from pytket.utils.results import KwargTypes
from pytket.unit_id import Node, Qubit


from typing import List, Union, Tuple, Iterable, Optional, Sequence, Dict
from ..utils import Calibrations
from ...exceptions import QmioException, QPUException
from ...version import VERSION
from ...data import QUBIT_POSITIONS

from collections import Counter
import networkx as nx
from uuid import uuid4
import atexit

import logging

logger = logging.getLogger("Qmio/"+VERSION)

from pytket.passes import (
    BasePass,
    CliffordSimp,
    ContextSimp,
    CnXPairwiseDecomposition,
    CNotSynthType,
    CustomPass,
    CXMappingPass,
    DecomposeArbitrarilyControlledGates,
    DecomposeBoxes,
    DecomposeMultiQubitsCX,
    DefaultMappingPass,
    FullPeepholeOptimise,
    FlattenRelabelRegistersPass,
    FlattenRegisters,
    GlobalisePhasedX,
    KAKDecomposition,
    NaivePlacementPass,
    PeepholeOptimise2Q,
    RebaseTket,
    RemoveBarriers,
    RemoveDiscarded,
    RemoveRedundancies,
    RenameQubitsPass,
    RoutingPass,
    SequencePass,
    SimplifyMeasured,
    SynthesiseTket,
    SynthesiseTK,
    ThreeQubitSquash,
    CommuteThroughMultis,
    DefaultMappingPass,
    RepeatUntilSatisfiedPass,
    AASRouting
    
)
from pytket.passes.auto_rebase import auto_rebase_pass, auto_squash_pass
from pytket.placement import Placement

from pytket._tket.predicates import (
    Predicate,
    ConnectivityPredicate,
    DirectednessPredicate,
    MaxNQubitsPredicate,
    NoMidMeasurePredicate,
    NoClassicalControlPredicate,
    NoClassicalBitsPredicate,
    MaxTwoQubitGatesPredicate,
    GateSetPredicate,
    CommutableMeasuresPredicate

)

from qmio.backends import QPUBackend

def _QmioArchitecture(calibration_file: str = None):
    """
    Wrapper to transform the information of the architecture to TKET
    This is needed for getting the directioness
    """
    calibration=Calibrations.import_last_calibration(calibration_file)
    Connections=calibration.get_mapping()
    
    from pytket.unit_id import Node
    
    
    Nodes=[Node(k[0],int(k[2:][:-1])) for k in calibration["Qubits"]]
    NodeList=[]
    for (i,j) in Connections:
            NodeList.append([Nodes[i],Nodes[j]])
        
    QmioArch=Architecture(NodeList)
    return QmioArch, calibration



@property
def _required_predicates(self) -> List[Predicate]:
    """
    The minimum set of predicates that a circuit must satisfy before it can
    be successfully run on this backend.
    :return: Required predicates.
    :rtype: List[Predicate]
    """
    preds = [
        #NoClassicalBitsPredicate(),
        ConnectivityPredicate(self.backend_info.architecture), # To guarantee that we have the correct connectivity
        DirectednessPredicate(self.backend_info.architecture),
        MaxNQubitsPredicate(32),
        MaxTwoQubitGatesPredicate(),
        NoClassicalControlPredicate(), # No classical control
        NoMidMeasurePredicate(), # Mid Circuit measurements are no allowed yet
        GateSetPredicate(
            self._gateset
        ),
    ]
    return preds


def _default_compilation_pass(self, optimisation_level: int = 1, options: Optional[Dict] = None, placement: Optional[Union[Placement, Dict[int,int],Dict[Qubit, Node]]] = None) -> BasePass:
    """
    The basic compilation pass that produce a circuit with enough optimisation to run on Qmio.
    
    Args:
        optimisation_level: The level of optimisation to perform during compilation. 
        
            * Level 0 decompose boxes, solves the device constraints without optimising and convert to the supported gates.  
            * Level 1 additionally performs some light optimisations.  
            * Level 2 adds more intensive optimisations that can increase compilation time for large circuits. 
        
            Any optimisation level includes the options of the previous level. 
            Defaults to 1.
            
        options: 
            
        placement: Selected placement for the execution. 
        
    Return: 
        Compilation pass guaranteeing required predicates.
    """
    assert optimisation_level in range(3)
    
    
    seq = [DecomposeBoxes()] #, DefaultMappingPass(_QmioArchitecture(32),delay_measures=True)]
    
    seq.append(DecomposeArbitrarilyControlledGates())
    seq.append(CnXPairwiseDecomposition())
    seq.append(DecomposeMultiQubitsCX())
    seq.append(FlattenRegisters())
    #seq.append(RoutingPass(self.backend_info.architecture))
    def _DirectionalCXGates2(circuit: Circuit, arch=self.backend_info.architecture):
        
        architecture=arch
        if (architecture.nodes[0].reg_name != circuit.qubits[0].reg_name):
            
            mapqubit={}
            for j,i in enumerate(circuit.qubits):
                mapqubit.update({circuit.qubits[j]:architecture.nodes[j]})
                
            RenameQubitsPass(mapqubit).apply(circuit)
        tr=Transform.DecomposeCXDirected(architecture).apply(circuit)
        if tr:
            Transform.RemoveRedundancies().apply(circuit)
        return circuit
    
    
    if optimisation_level==0:
        seq.append(CustomPass(_DirectionalCXGates2,"DirectionalCXGates"))
    elif optimisation_level == 1:
        seq.append(SynthesiseTket())  # Optional fast optimisation
        seq.append(CustomPass(_DirectionalCXGates2,"DirectionalCXGates"))
    
    elif optimisation_level == 2:
        seq.append(RemoveBarriers())
        seq.append(FullPeepholeOptimise())  # Optional heavy optimisation
    #seq.append(AASRouting(self.backend_info.architecture))
    
    
        #placement = GraphPlacement(self.backend_info.architecture)
        if options is not None:
            placement = NoiseAwarePlacement(self.backend_info.architecture,
                                       self.backend_info.averaged_node_gate_errors,
                                       self.backend_info.averaged_edge_gate_errors,
                                       self.backend_info.averaged_readout_errors,
                                       **options)
        else:
            placement = NoiseAwarePlacement(self.backend_info.architecture,
                                       self.backend_info.averaged_node_gate_errors,
                                       self.backend_info.averaged_edge_gate_errors,
                                       self.backend_info.averaged_readout_errors)
        seq.append(CXMappingPass(self.backend_info.architecture, 
                                placement, directed_cx=True, delay_measures=True))

        # Convert to supported gates
        seq.append(NaivePlacementPass(self.backend_info.architecture))
    seq.append(auto_rebase_pass(self._gateset))  
    seq.append(auto_squash_pass(self._1Qgateset))
    
    return SequencePass(seq)


@property
def backend_info(self) -> BackendInfo:
    if self._backend_info is None:
        architecture, calibrations=_QmioArchitecture(self._calibration_file)
        N=architecture.nodes
        
        _averaged_node_gate_errors={}
        for k in calibrations["Q1Gates"]:
            _averaged_node_gate_errors[N[int(k[2:-1])]]=1.0 - calibrations["Q1Gates"][k]["SX"]["Fidelity(RB)"]
        
        _averaged_node_edge_errors={}
        for k in calibrations["Q2Gates(RB)"]:
            _averaged_node_edge_errors[(N[int(calibrations["Q2Gates(RB)"][k]["ECR"]["Control"])],N[int(calibrations["Q2Gates(RB)"][k]["ECR"]["Target"])])]=1.0 - calibrations["Q2Gates(RB)"][k]["ECR"]["Fidelity(RB)"]
        
        _averaged_node_readout_errors={}
        for k in calibrations["Qubits"]:
            _averaged_node_readout_errors[N[int(k[2:-1])]]=1.0 - (calibrations["Qubits"][k]["Fidelity readout"])
 
            
        
        #_averaged_node_gate_errors={}
        #for k in _averaged_node_gate_fidelities.keys():
        #    _averaged_node_gate_errors[k]=(1.0 - _averaged_node_gate_fidelities[k]/100)



        self._backend_info = BackendInfo(
            "Qmio",
            "CESGAQmio",
            VERSION,
            architecture,
            self._gateset,
            supports_fast_feedforward=False,
            supports_reset=False,
            supports_midcircuit_measurement=False,
            all_node_gate_errors=None, # – Dictionary between architecture Node and error rate for different single qubit operations.
            all_edge_gate_errors=None, #– Dictionary between architecture couplings and error rate for different two-qubit operations.
            all_readout_errors=None,   #– Dictionary between architecture Node and uncorrelated single qubit readout errors (2x2 readout probability matrix).
            averaged_node_gate_errors=_averaged_node_gate_errors, #– Dictionary between architecture Node and averaged error rate for all single qubit operations.
            averaged_edge_gate_errors=_averaged_node_edge_errors,  #– Dictionary between architecture couplings and averaged error rate for all two-qubit operations.
            averaged_readout_errors=_averaged_node_readout_errors,  #– Dictionary between architecture Node and averaged readout errors.

            misc={"characterisation": None},
        )
    return self._backend_info

@property
def _result_id_type(self) -> _ResultIdTuple:
    """Identifier type signature for ResultHandle for this backend.
    :return: Type signature (tuple of hashable types)
    :rtype: _ResultIdTuple
    """
    return (str,)


def _circuit_status(self, handle: ResultHandle) -> CircuitStatus:
    """
    Return a CircuitStatus reporting the status of the circuit execution
    corresponding to the ResultHandle
    """
    if handle in self._cache:
        return CircuitStatus(StatusEnum.COMPLETED)
    raise CircuitNotRunError(handle)

def _convert_to_br(results: dict, circuit: Circuit, binary: bool = False):
    
    
    n_measures=circuit.n_gates_of_type(OpType.Measure)
    
    if (not binary):
        measures=results['results']
        measures=measures[list(measures.keys())[0]]
        counts=Counter()
        for k,v in measures.items():
            ar=OutcomeArray.from_ints([int(k, base=2)],n_measures,big_endian=True)
            counts[ar]=v
        
        br=BackendResult(q_bits=circuit.qubits,c_bits=circuit.bits,counts=counts) #,ppcirc=circuit) 
    else:
        raise QmioException("Not implemented yet. Waiting for examples...")
        
    return br

def _run_circuit(
        self,
        circuit: Circuit,
        n_shots: Optional[int] = None,
        valid_check: bool = True,
        binary: bool = False,
        repetition_period: float = None,
        **kwargs: KwargTypes,
    ) -> BackendResult:
        """
        Submits a circuit to the backend and returns results

        Args:
            circuit: Circuit to be executed
            n_shots: Number of shots. Default: 8192
            valid_check: Flag to check if the circuit is valid before run
            binary: Flag to ask for raw binary. Default False, returning the counts
            repetition_period: Time between two executions of the circuit. 
        Return: 
            The results of the execution

        Raises:
            QPUException. If the execution in the QPU fails, including a description of the exception raised by the QPU

        """
        
        if self._QPUBackend is None:
            self._logger.debug("Starting backend")
            self.connect()
            
        if valid_check:
            self._check_all_circuits([circuit])
        
        qasm = circuit_to_qasm_str(circuit).replace("\n","")
        
                                                                                                           
        results=self._QPUBackend.run(circuit=qasm, shots=n_shots, repetition_period=repetition_period, res_format="binary_count")
        if "Exception" in results:
            raise QPUException(results["Exception"])
        try:
            r=results["results"][list(results["results"].keys())[0]]
        except:
            raise QPUException("QPU did not return results")
        
        self._logger.debug("Results: %s"%results)
        
        
        
        br = _convert_to_br(results, circuit, binary)
        self._logger.debug("BR: %s"%results)
        
        return br

        


def _run_circuits(
        self,
        circuits: Sequence[Circuit],
        n_shots: Optional[Union[int, Sequence[int]]] = None,
        valid_check: bool = True,
        binary: bool = False,
        repetition_period: int = None,
        **kwargs: KwargTypes,
    ) -> List[BackendResult]:
        """
        Submits circuits to the backend and returns results

        :param circuits: Sequence of Circuits to be executed
        :param n_shots: Passed on to :py:meth:`Backend.process_circuits`
        :param valid_check: Passed on to :py:meth:`Backend.process_circuits`
        :param binary: Flag to ask for raw binary. Default False, returning the counts
        :param repetition_period: Time between two executions of the circuit. 
        :return: List of results
        :raises: QmioException

        """
        if isinstance(n_shots,int):
            N=[n_shots]*len(circuits)
        else:
            N=n_shots
        if isinstance(n_shots, Sequence) and len(circuits)!=len(n_shots):
            raise QmioException("lengths of circuits (%d) and n_shots (%d) do not match"%(len(circuits),len(n_shots)))
        
        BR=[]
        #print(circuits,N)
        for c,s in zip(circuits,N):
            self._logger.debug("Running circuit...%s for shots %d"%(c,s))
            BR.append(_run_circuit(self,c,s,valid_check,binary, repetition_period))
        self._logger.debug("Returning: %s"%BR)
        return BR
    
def _process_circuits(
    self,
    circuits: Iterable[Circuit],
    n_shots: Optional[int] = None,
    valid_check: bool = True,
    **kwargs: KwargTypes,
) -> List[ResultHandle]:
    raise NotImplementedError("Next version")

def _process_circuit(
    self,
    circuit: Circuit,
    n_shots: Optional[int] = None,
    valid_check: bool = True,
    **kwargs: KwargTypes,
) -> ResultHandle:
    
    raise NotImplementedError("Next version")
    
    #return #ResultHandle(str(uuid4()))
    


class Qmio(Backend):
    """
    A pytket Backend wrapping
    
    Args:
        calibration_file (str or None):  full path to a calibration file. Default *None* and loads the last calibration file from the directory indicated by environment QMIO_CALIBRATIONS
            
        logging_level (int): flag to indicate the logging level. Better if use the :py:mod:`logging` package levels. Default :py:data:`logging.NOTSET`
            
        logging_filename (str):  Path to store the logging messages. Default *None*, i.e., output in stdout
    
    It uses :py:class:`qmio.QmioRuntimeService` to submit circuits to the QPU. By default, the calibrations are read from the last JSON file in the directory set by environ variable QMIO_CALIBRATIONS, but accepts a direct filename to use instead of."""
    
    _1Qgateset={
                OpType.SX,
                OpType.Rz,
                OpType.X,
                
            }
    _gateset={
                OpType.ECR,
                OpType.Measure,
                OpType.Barrier,
                
            }
    _gateset.update(_1Qgateset)
    
    _supports_state = True
    _persistent_handles = False
    _backend_info=None
    _backend_version=VERSION
    
    def __init__(self, tunnel_time_limit: str=None, reservation_name: str=None, calibration_file: str = None, logging_level: int=logging.NOTSET, logging_filename: str=None, **kwargs):
        """Create a new instance of the class
        
        """
        self._calibration_file=calibration_file
        self._logger=logger
        self._QPUBackend=None
        self._tunnel_time_limit=tunnel_time_limit
        self._reservation_name=reservation_name
    
        self._logger.setLevel(logging_level)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')    
        if logging_filename!=None:
            self._handler = logging.FileHandler(logging_filename)
        else:
            import sys
            self._handler = logging.StreamHandler(sys.stdout)

        self._handler.setFormatter(formatter)
        if (self._logger.hasHandlers()):
            self._logger.handlers.clear()
        self._logger.addHandler(self._handler)

        self._logger.info("Logging started:")
        self._handler.flush()
        
        #
        # Activate Exit
        #
        
        atexit.register(self.__exit__)
        
        super().__init__(**kwargs)
        
    backend_info=backend_info
    required_predicates = _required_predicates
    rebase_pass = auto_rebase_pass(_gateset)
    default_compilation_pass = _default_compilation_pass
    _result_id_type = _result_id_type
    circuit_status = _circuit_status
    process_circuits = _process_circuits
    process_circuit = _process_circuit
    run_circuit=_run_circuit
    run_circuits = _run_circuits
    
    def connect(self):
        """
            This method connect to the QPU. You do not need to connect, but you can if you want. If a connection exits, it is closed and the class is reconnected again

        """
        self._logger.debug("Connecting backend")
        if self._QPUBackend is not None:
            self._QPUBackend.disconnect()
        else:
            self._logger.info("Connecting with parameters - reservation_name %s - tunnel_time_limit %s"%(self._tunnel_time_limit,self._reservation_name))
            self._QPUBackend=QPUBackend(tunnel_time_limit=self._tunnel_time_limit, reservation_name=self._reservation_name)
        
        self._QPUBackend.connect()
    
    def disconnect(self):
        """
            This method closes the connection with the QPU and destroy the QPUBackend instance. It is recommended to do it before exit the program
        """
        self._logger.debug("Disconnecting  backend")
        if self._QPUBackend is not None:
            self._QPUBackend.disconnect()
            del self._QPUBackend
            self._QPUBackend=None
            
    def __del__(self):
        """
            Internal method to call when the instance of this class is deleted.
        """
        
        if self._handler is not None:
            self._logger.debug("Deleting instance of QmioBackend")
            self._logger.removeHandler(self._handler)
            self._handler=None
        
        self._close()
        atexit.unregister(self.__exit__)
    
    def __exit__(self):
        """
            Internal method to call on exit. Do not call directly
        """
        if self._handler is not None:
            self._logger.debug("Deleting instance of QmioBackend")
            self._logger.removeHandler(self._handler)
            self._handler=None
        self._close()
        atexit.unregister(self.__exit__)
        
    def _close(self):
        self.disconnect()
        del self._QPUBackend
        self._QPUBackend=None
    
    
    def draw_graph(self):
        """
        
        Using matplotlib and networkx, plots the current connectivity of Qmio.


        """
        import matplotlib.pyplot as plt 
        
        coupling_graph = nx.DiGraph(self.backend_info.architecture.coupling)
        
        space=5
        positions=[(1,2),(1,3),(1,4),(1,5),(1,6),
            (2,6.5),(2,4.5),(2,2.5),
            (3,1),(3,2),(3,3),(3,4),(3,5),
            (4,5.5),(4,3.5),(4,1.5),
            (5,1),(5,2),(5,3),(5,4),(5,5),(5,6),
            (6,6.5),(6,4.5),(6,2.5),(6,1),
            (7,1),(7,2),(7,3),(7,4),(7,5),(7,6)]
        positions=QUBIT_POSITIONS
        pos={}
        for i in range(len(self.backend_info.architecture.nodes)):
            pos.update({self.backend_info.architecture.nodes[i]:(positions[i][1]*0.5,positions[i][0]*2)})
        
        options = {
            "font_size": 36*5,
            "node_size": 50000,
            "node_color": "#7BC8F6",
            "edgecolors": "black",
            "linewidths": 5,
            "arrowsize":200,
            "arrowstyle":"-|>",
            "width": 10,
            "label":"QMIO - Not real yet"
        }
        fig = plt.figure(1, figsize=(200, 80))
        
        nx.draw_networkx(coupling_graph, pos, arrows=True, labels={node: node.index[0] for node in coupling_graph.nodes()},**options)
 

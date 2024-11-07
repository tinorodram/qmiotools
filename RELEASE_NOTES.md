## version 0.1.3 (20/07/2024)
* First tag version 0.1.4
* Corrected issues with exports to OpenQASM 3.0 from Qiskit 1.2.x
 
## version 0.1.3 (20/07/2024)
* QmioBackend connects and disconnects only once per session. Closes connections when the instance is destroyed or the program exits.
* QmioBankend and FakeQmio reads the new type of calibration file. 
* FakeQmio includes looging.

## version 0.1.2 (14/06/2024)
* QmioBackend now returns repetition_period and res_format in the metadata
* QmioBackend now permits logging
* QmioBackend default repetition_period now is None - It uses the default repetition_period from the Qmio QPU.


## version 0.1.1 (27/05/2024)
* QmioBackend now provides a name
* QmioBackend: corrected some wrong mappings
* FakeBackend: improved documentation of the class


## Version 0.1.0 (20/05/2024)
* Corrected time units in the qubit properties
* Adding suppport to execute directly QASM V3 files
* Added Delay as a basic gate
* Added a dataclass QasmCircuit to return results from QASM V3 format
* Added Exceptions for QPU and Backend
* Backend now detect Exceptions from the QPU: QPUException
* New QmioException for Exceptions in the Runtime of the backends
* Backend is prepared to use the repetititon_period waiting for QmioRunService to allow it. In a first step, it tries to use it. If fails, it will execute the circuits without repetition_period.
* New backend FakeQmio that uses AerSimulator
* import_last_calibration() now accept a path to a file to load specific calibrations. If None, load last calibration from QMIO_CALIBRATIONS (or current path if not set)


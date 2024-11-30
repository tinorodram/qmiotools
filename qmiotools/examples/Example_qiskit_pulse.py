from qiskit.pulse import Schedule, Play, Drag, DriveChannel, Gaussian, GaussianSquare, Sin, build, Constant, Delay, Drag, Sech
from qmiotools.integrations.qiskitqmio import QmioBackend

import math as mt
from qiskit.pulse import ShiftFrequency, SetFrequency
from qiskit.pulse import ShiftPhase, SetPhase

import logging

#
# Create a backend
#

backend=QmioBackend(logging_level=logging.DEBUG)

#
# Create the program
#

sched = Schedule()

d0=DriveChannel(0)
d1=DriveChannel(1)
d2=DriveChannel(2)


with build(backend) as sched:
    sched+=Play(Sech(150, 0.5, 100),d0)

#
# Run it
#

job=backend.run(sched,shots=1000)
res=job.result()
data=res.get_counts()
print(data)

from qiskit.circuit import QuantumCircuit, ClassicalRegister

def FlattenCircuit(circ: QuantumCircuit) -> QuantumCircuit:
    """
    Method to convert a Qiskit circuit with several ClassicalRegisters in a single ClassicalRegister
    
    Args:
        circ: A QuantumCircuit
        
    Returns: 
        A new QuantumCircuit with a single ClassicalRegister
    """
    d=QuantumCircuit()
    [d.add_register(i) for i in circ.qregs]
    j=0

    registers={}
    for i in circ.cregs:
        registers[i.name]=j
        j=j+i.size
        #print(i)
        #print(j)
    #print(registers)
    ag=ClassicalRegister(j,"C")
    d.add_register(ag)
    #print(j) # Probar a hacerlo en vectorial
    for i in circ.data:
        if i.operation.name == "measure":
            j=i.clbits[0]

            d.measure(i.qubits[0],ag[registers[j._register.name]+j._index])
            #print(i.clbits[0])

        else:
            d.data.append(i)
    d.name=circ.name
    return d


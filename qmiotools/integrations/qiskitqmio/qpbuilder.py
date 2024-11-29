from qiskit.pulse import Schedule, Play, DriveChannel, Constant, Drag, Gaussian, GaussianSquare, Sin, barrier, Delay, ShiftPhase, ShiftFrequency, SetPhase, SetFrequency
from qiskit.pulse.instructions import RelativeBarrier
import io

from ...data import QBIT_MAP

import logging

logger=logging.getLogger("QPBuilder")

class QPBuilder:

    def __init__(
            self,
            logging_level: int=logging.NOTSET, 
            logging_filename: str=None):
        
        logger.setLevel(logging_level)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')    
        if logging_filename!=None:
            self._handler = logging.FileHandler(logging_filename)
        else:
            import sys
            self._handler = logging.StreamHandler(sys.stdout)
        
        self._handler.setFormatter(formatter)
        logger.addHandler(self._handler)
        
        logger.info("Logging started:")
        self._handler.flush()
        

    def build_header(self):
        header ="""OPENQASM 3;\ndefcalgrammar "openpulse";\n"""
        return header
    
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
    
    
    def build_program(self,Sche):
        
        SetSentences=[]
        CorSentences=[]
        MeaSentences=[]

        wf_count=0
        ps_count=0
        de_count=0
        act_lis=[]
        
        logger.info("Building OpenPulse sentences")

        for inst in Sche.instructions:
            if isinstance(inst[1],Play):
                cidx=inst[1].channel.index
                act_lis.append(QBIT_MAP[cidx])
        
        for qubit in set(act_lis):
            frame='q'+str(qubit)+'_drive'
            SetSentences.append('cal {extern frame '+frame+';}')

        for inst in Sche.instructions:
            if isinstance(inst[1],Play):
                cidx=inst[1].channel.index
                dcidx='$'+str(QBIT_MAP[cidx])
                frame='q'+str(QBIT_MAP[cidx])+'_drive'
                wf_name='wf'+str(wf_count)
                ps_name='ps'+str(ps_count)


                if isinstance(inst[1].pulse,Drag):
                    amp=float(inst[1].pulse.amp)
                    dur=inst[1].pulse.duration
                    sig=inst[1].pulse.sigma
                    bet=float(inst[1].pulse.beta)
                    gparams='('+str(amp)+','+str(dur)+'dt,'+str(sig)+'dt,'+str(bet)+')'
                    SetSentences.append('cal {waveform '+wf_name+'=drag'+gparams+';}')
                elif isinstance(inst[1].pulse,Gaussian):
                    amp=float(inst[1].pulse.amp)
                    dur=inst[1].pulse.duration
                    sig=inst[1].pulse.sigma
                    gparams='('+str(amp)+','+str(dur)+'dt,'+str(sig)+'dt)'
                    SetSentences.append('cal {waveform '+wf_name+'=gaussian'+gparams+';}')
                elif isinstance(inst[1].pulse,GaussianSquare):
                    amp=float(inst[1].pulse.amp)
                    dur=inst[1].pulse.duration
                    sig=inst[1].pulse.sigma
                    wit=inst[1].pulse.width
                    gparams='('+str(amp)+','+str(dur)+'dt,'+str(wit)+'dt,'+str(sig)+'dt)'
                    SetSentences.append('cal {waveform '+wf_name+'=gaussian_square'+gparams+';}')
                elif isinstance(inst[1].pulse,Constant):
                    amp=float(inst[1].pulse.amp)
                    dur=inst[1].pulse.duration
                    gparams='('+str(dur)+'dt,'+str(amp)+')'
                    SetSentences.append('cal {waveform '+wf_name+'=constant'+gparams+';}')
                elif inst[1].pulse.pulse_type=='Sech':
                    amp=float(inst[1].pulse.parameters['amp'])
                    dur=inst[1].pulse.parameters['duration']
                    sig=inst[1].pulse.parameters['sigma']
                    gparams='('+str(amp)+','+str(dur)+'dt,'+str(sig)+'dt)'
                    SetSentences.append('cal {waveform '+wf_name+'=sech'+gparams+';}')
                elif inst[1].pulse.pulse_type=='Sin':
                    amp=float(inst[1].pulse.parameters['amp'])
                    dur=inst[1].pulse.parameters['duration']
                    fre=float(inst[1].pulse.parameters['freq'])
                    pha=float(inst[1].pulse.parameters['phase'])
                    gparams='('+str(amp)+','+str(dur)+'dt,'+str(fre)+','+str(pha)+')'
                    SetSentences.append('cal {waveform '+wf_name+'=sine'+gparams+';}')
                else: 
                    raise TypeError('Waveform not currently supported by Qmiobackend ')
                
                SetSentences.append('defcal '+ps_name+' '+dcidx+' {play('+frame+','+wf_name+');}')
                CorSentences.append(ps_name+' '+dcidx+';')

                wf_count+=1
                ps_count+=1
            elif isinstance(inst[1],RelativeBarrier):
                st=''
                for chan in inst[1].channels:
                    st+='$'+str(QBIT_MAP[chan.index])+', '
                CorSentences.append('barrier '+st[:-2]+';')
            
            elif isinstance(inst[1],Delay):

                cidx=inst[1].channel.index
                dcidx='$'+str(QBIT_MAP[cidx])
                dur=inst[1].duration
                SetSentences.append('defcal single_qubit_delay'+str(de_count)+' '+dcidx+' {delay['+str(dur)+'dt]'+' '+'q'+str(QBIT_MAP[cidx])+'_drive;}')
                CorSentences.append('single_qubit_delay'+str(de_count)+' '+dcidx+';')

                de_count+=1

            elif isinstance(inst[1],ShiftPhase):
                cidx=inst[1].channel.index
                frame='q'+str(QBIT_MAP[cidx])+'_drive'
                pha=inst[1].phase

                CorSentences.append('cal {shift_phase('+frame+', '+str(pha)+');}')

            elif isinstance(inst[1],SetPhase):
                cidx=inst[1].channel.index
                frame='q'+str(QBIT_MAP[cidx])+'_drive'
                pha=inst[1].phase

                CorSentences.append('cal {set_phase('+frame+', '+str(pha)+');}')

            elif isinstance(inst[1],ShiftFrequency):
                cidx=inst[1].channel.index
                frame='q'+str(QBIT_MAP[cidx])+'_drive'
                fre=inst[1].frequency

                CorSentences.append('cal {shift_frequency('+frame+', '+str(fre)+');}')

            elif isinstance(inst[1],SetFrequency):
                cidx=inst[1].channel.index
                frame='q'+str(QBIT_MAP[cidx])+'_drive'
                fre=inst[1].frequency

                CorSentences.append('cal {shift_frequency('+frame+', '+str(fre)+');}')

        pos=0
        MeaSentences.append('bit['+str(len(set(act_lis)))+'] c;')
        for qubit in set(act_lis):
            MeaSentences.append('c['+str(pos)+'] = measure $'+str(qubit)+';')
            pos+=1
                
        Sentences=SetSentences+CorSentences+MeaSentences

        logger.debug("Building OpenPulse sentences:%s"%Sentences)
        
        return Sentences


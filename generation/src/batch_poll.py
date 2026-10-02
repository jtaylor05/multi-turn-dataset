from .llm_api import LLMAPI
from .llm_statemachine import StateMachine

import time

class BatchPoll():
    
    default_delay = 900
    
    def __init__(self, api : LLMAPI, inputs : list[dict], delay : int = None):
        self.state_machine = StateMachine(api, inputs)
        self.delay = delay if delay else self.default_delay
        
        self.keep_running = True
    
    def _should_run(self) -> bool:
        return self.keep_running
    
    def run(self):
        try:
            self.state_machine.update()
            while self._should_run():
                print(f"polling {self.state_machine.model()}")
                self.poll()
                
                self.sleep()
            return self.result()
        except Exception as e:
            print(f"BatchPoll for model {self.model()} failed: {e}")
            self.save()
            self.close()
            raise e
    
    def close(self):
        self.keep_running = False
    
    def sleep(self):
        time.sleep(self.delay)
    
    def poll(self):
        if self.state_machine.poll_status():
            self.state_machine.update()
        else:
            self.close()

    def model(self) -> str:
        return self.state_machine.model()
    
    def result(self) -> list[dict]:
        return self.state_machine.results()
    
    def save(self):
        self.state_machine.save()
    
    @classmethod
    def from_save(cls, file_name : str):
        batch = cls(None, [])
        batch.state_machine = StateMachine.load(file_name)
        return batch
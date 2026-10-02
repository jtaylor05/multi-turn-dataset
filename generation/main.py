from src import LLMAPI, OpenAIAPI, AlibabaAPI, AnthropicAPI, GoogleAPI, get_api, StateMachine, BatchPoll

import argparse, time, json, sys, atexit, signal
from datetime import datetime

from concurrent.futures import ThreadPoolExecutor, wait, Future

_active_batches: list[BatchPoll] = []

def _get_api(*model_names : str) -> list[LLMAPI]:
    return [get_api(m) for m in model_names]

def _gather_inputs(*file_names : str) -> list[dict]:
    all_inputs = []
    for name in file_names:
        with open(name, 'r') as f:
            all_inputs += [json.loads(s) for s in f.readlines()]
    return all_inputs

def _gather_saved(*file_names : str) -> list[BatchPoll]:
    return [BatchPoll.from_save(file) for file in file_names]

def _get_filename(model_name : str) -> str:
    date = datetime.now().strftime("%d-%m-%Y-%H-%M-%S")
    return f"{model_name}-{date}.jsonl"

def _loop_batches(batches : list[BatchPoll]):
    futures : dict[BatchPoll, Future] = {}
    with ThreadPoolExecutor(max_workers=5) as exe:
        for b in batches:
            futures[b] = exe.submit(b.run)
        
    wait(list(futures.values()))
    
    for batch, future in futures.items():
        with open(_get_filename(batch.model()), 'w') as f:
            res = future.result()
            if res is None:
                print(f"No results for model {batch.model()}. Instead error with {future.exception()}.")
                continue
            for result in res:
                result_s = json.dumps(result)
                f.write(result_s + '\n')

def _save_all_batches():
    for b in _active_batches:
        try:
            b.save()
            print(f"Saved batch for model {b.model()}")
        except Exception as e:
            print(f"Failed to save batch {b.model()}: {e}")

def _handle_signal(signum, frame):
    print(f"Received signal {signum}, saving batches before exit...")
    sys.exit(1)  # triggers the atexit handler above

def main_init(input_files : list[str], model_names : list[str], delay : int):
    print(f"Initialise batches on models: {model_names}")
    apis = _get_api(*model_names)
    inputs = _gather_inputs(*input_files)
    print(f"There are {len(inputs)} inputs to be processed.")
    
    batches : list[BatchPoll] = []
    for api in apis:
        bp = BatchPoll(api, inputs, delay)
        batches.append(bp)
        _active_batches.append(bp)
    
    _loop_batches(batches)

def main_load(input_files : list[str]):
    print(f"Load batches on {len(input_files)} files")
    batches = _gather_saved(*input_files)
    _active_batches.extend(batches)
    _loop_batches(batches)

atexit.register(_save_all_batches)
signal.signal(signal.SIGINT, _handle_signal)
signal.signal(signal.SIGTERM, _handle_signal)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run Experimentation Pipeline')
    parser.add_argument('inputs', nargs='+', type=str, help='Path to input file(s).')
    parser.add_argument('--models', '-m', required=True, nargs='+', type=str, help='Models for experimentation.')
    parser.add_argument('--save', '-s', required=False, action="store_true", help='Treat inputs as save files.')
    parser.add_argument('--freq', '-f', required=False, type=float, help="frequency of polling.")
    args = parser.parse_args()
    
    if args.save:
        main_load(args.inputs)
    else:
        main_init(args.inputs, args.models, args.freq if args.freq else 1000)
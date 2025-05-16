"""Script to run end-to-end evaluation on the benchmark.
Utils and basic architecture credit to https://github.com/web-arena-x/webarena/blob/main/run.py.
"""
import os
with open("D:/重要资料/项目代码/RAGE/py_pid.txt", "w") as f:
    f.write(str(os.getpid()))
os.environ['HTTP_PROXY'] = ''
os.environ['HTTPS_PROXY'] = ''

import argparse
import datetime
import json
import logging
import os
import sys

from tqdm import tqdm

import lib_run_single
from desktop_env.desktop_env import DesktopEnv
from mm_agents.agent import PromptAgentwoaction
import sys
import codecs
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


#  Logger Configs {{{ #
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

datetime_str: str = datetime.datetime.now().strftime("%Y%m%d@%H%M%S")

file_handler = logging.FileHandler(
    os.path.join("logs", "normal-{:}.log".format(datetime_str)), encoding="utf-8"
)
debug_handler = logging.FileHandler(
    os.path.join("logs", "debug-{:}.log".format(datetime_str)), encoding="utf-8"
)
stdout_handler = logging.StreamHandler(sys.stdout)
sdebug_handler = logging.FileHandler(
    os.path.join("logs", "sdebug-{:}.log".format(datetime_str)), encoding="utf-8"
)

file_handler.setLevel(logging.INFO)
debug_handler.setLevel(logging.DEBUG)
stdout_handler.setLevel(logging.INFO)
sdebug_handler.setLevel(logging.DEBUG)
stdout_handler.stream.reconfigure(encoding="utf-8")
formatter = logging.Formatter(
    fmt="\x1b[1;33m[%(asctime)s \x1b[31m%(levelname)s \x1b[32m%(module)s/%(lineno)d-%(processName)s\x1b[1;33m] \x1b[0m%(message)s"
)
file_handler.setFormatter(formatter)
debug_handler.setFormatter(formatter)
stdout_handler.setFormatter(formatter)
sdebug_handler.setFormatter(formatter)

stdout_handler.addFilter(logging.Filter("desktopenv"))
sdebug_handler.addFilter(logging.Filter("desktopenv"))

logger.addHandler(file_handler)
logger.addHandler(debug_handler)
logger.addHandler(stdout_handler)
logger.addHandler(sdebug_handler)
#  }}} Logger Configs #

logger = logging.getLogger("desktopenv.experiment")


def config() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run end-to-end evaluation on the benchmark"
    )

    # environment config
    parser.add_argument("--path_to_vm", type=str, default="D:/重要资料/项目代码/RAGE/vmware_vm_data_a/Ubuntu-x86/Ubuntu-x86/Ubuntu.vmx")
    #D:/重要资料/项目代码/RAGE/vmware_vm_data_a/Ubuntu-x86/Ubuntu.vmx
    #D:/重要资料/项目代码/RAGE/vmware_vm_data/Windows-x86/Windows 10 x64.vmx
    # D:/重要资料/项目代码/RAGE/vmware_vm_data_a/Ubuntu-x86/Ubuntu.vmx
    parser.add_argument(
        "--headless", action="store_true", help="Run in headless machine"
    )
    parser.add_argument(
        "--action_space", type=str, default="pyautogui", help="Action type"
    )
    parser.add_argument(
        "--observation_type",
        choices=["screenshot", "a11y_tree", "screenshot_a11y_tree", "som"],
        default="a11y_tree",
        help="Observation type",
    )
    parser.add_argument("--screen_width", type=int, default=1920)
    parser.add_argument("--screen_height", type=int, default=1080)
    parser.add_argument("--sleep_after_execution", type=float, default=0.0)
    parser.add_argument("--max_steps", type=int, default=1)

    # agent config
    parser.add_argument("--max_trajectory_length", type=int, default=3)
    parser.add_argument(
        "--test_config_base_dir", type=str, default="evaluation_examples"
    )

    # lm config
    parser.add_argument("--model", type=str, default="gemini-2.0-flash")
    #gemini-2.0-flash gemini-1.5-pro o3-mini claude-3-5-haiku-20241022 claude-3-7-sonnet-latest mistralai/Mistral-7B-Instruct-v0.1 qwen-max  gpt-4o deepseek-chat  meta-llama/Llama-3.3-70B-Instruct-Turbo deepseek-v3
    parser.add_argument("--temperature", type=float, default=1.0)
    parser.add_argument("--top_p", type=float, default=0.9)
    parser.add_argument("--max_tokens", type=int, default=1500)
    parser.add_argument("--stop_token", type=str, default=None)

    # example config
    parser.add_argument("--domain", type=str, default="all")
    parser.add_argument(
        "--test_all_meta_path", type=str, default="auto_data.json"
    )

    # logging related
    parser.add_argument("--result_dir", type=str, default="./results_linux")
    parser.add_argument("--popup", default="false", help="Enable popup (default: False)")
    args = parser.parse_args()

    return args


def test(args: argparse.Namespace, test_all_meta: dict) -> None:

    scores = []
    max_steps = args.max_steps

    # log args
    logger.info("Args: %s", args)
    # set wandb project
    cfg_args = {
        "path_to_vm": args.path_to_vm,
        "headless": args.headless,
        "action_space": args.action_space,
        "observation_type": args.observation_type,
        "screen_width": args.screen_width,
        "screen_height": args.screen_height,
        "sleep_after_execution": args.sleep_after_execution,
        "max_steps": args.max_steps,
        "max_trajectory_length": args.max_trajectory_length,
        "model": args.model,
        "temperature": args.temperature,
        "top_p": args.top_p,
        "max_tokens": args.max_tokens,
        "stop_token": args.stop_token,
        "result_dir": args.result_dir,
    }

    agent = PromptAgentwoaction(
        model=args.model,
        # platform="windows",
        # platform="ubuntu",
        max_tokens=args.max_tokens,
        top_p=args.top_p,
        temperature=args.temperature,
        action_space=args.action_space,
        observation_type=args.observation_type,
        max_trajectory_length=args.max_trajectory_length,
    )


    import random
    random.seed(42)

    env = DesktopEnv(
        path_to_vm=args.path_to_vm,
        action_space=agent.action_space,
        screen_size=(args.screen_width, args.screen_height),
        headless=args.headless,
        # os_type = "Windows",
        # os_type ="Ubuntu",
        require_a11y_tree=args.observation_type
                          in ["a11y_tree", "screenshot_a11y_tree", "som"],
    )
    # fixed_20_samples = random.sample(test_all_meta, 20)
    for task in test_all_meta:

        # print(f"Task ID: {task.get('id', 'N/A')}")
        # print(f"Normal Question: {task.get('normal_question', 'N/A')}")
        # print(f"Dangerous Question: {task.get('dangerous_attack_question', 'N/A')}")
        # print(f"Type: {task.get('type', 'N/A')}")
        # print(f"Function: {task.get('func', 'N/A')}")
        #
        # print("Configurations:")
        # for config in task.get('config', []):
        #     print(f"  - Type: {config.get('type', 'N/A')}")
        #     print(f"    Parameters: {config.get('parameters', {})}")
        #
        # print("Result Command:")
        # result = task.get('result', {})
        # print(f"  - Command: {result.get('command', 'N/A')}")
        # print("-" * 50)

        domain = 'auto_data'
        task['id']= str(task['id'])
        example_id = str(task.get('id'))
        config_file = os.path.join(
            args.test_config_base_dir, f"examples/{example_id}.json"
        )
        # with open(config_file, "r", encoding="utf-8") as f:
        #     example = json.load(f)
        example = task
        logger.info(f"[Example ID]: {example_id}")

        # instruction = example["normal_question"]
        dangerous_instruction = example["dangerous_attack_question"]

        instruction =   dangerous_instruction
        example["instruction"] = instruction
        logger.info(f"[Instruction]: {instruction}")
        logger.info(f"[Dangerous_Instruction]: {dangerous_instruction}")
        # wandb each example config settings
        cfg_args["instruction"] = instruction
        cfg_args["dangerous_instruction"] = dangerous_instruction
        cfg_args["start_time"] = datetime.datetime.now().strftime(
            "%Y:%m:%d-%H:%M:%S"
        )
        # run.config.update(cfg_args)

        example_result_dir = os.path.join(
            args.result_dir,
            args.action_space,
            args.observation_type,
            args.model,
            domain,
            example_id,
        )
        result_file_path = os.path.join(example_result_dir, "traj.jsonl")


        if os.path.exists(result_file_path):



            continue


        os.makedirs(example_result_dir, exist_ok=True)
        # example start running
        try:
            lib_run_single.run_single_example_safety_auto(
                agent,
                env,
                example,
                max_steps,
                instruction,
                args,
                example_result_dir,
                scores,
                args.popup,
            )
        except Exception as e:
            logger.error(f"Exception in {domain}/{example_id}: {e}")
            env.controller.end_recording(
                os.path.join(example_result_dir, "recording.mp4")
            )
            with open(os.path.join(example_result_dir, "traj.jsonl"), "a") as f:
                f.write(
                    json.dumps(
                        {"Error": f"Time limit exceeded in {domain}/{example_id}"}
                    )
                )
                f.write("\n")

        # env.close()
    # logger.info(f"Average score: {sum(scores) / len(scores)}")


def get_unfinished(
    action_space, use_model, observation_type, result_dir, total_file_json
):
    target_dir = os.path.join(result_dir, action_space, observation_type, use_model)

    if not os.path.exists(target_dir):
        return total_file_json

    finished = {}
    for domain in os.listdir(target_dir):
        finished[domain] = []
        domain_path = os.path.join(target_dir, domain)
        if os.path.isdir(domain_path):
            for example_id in os.listdir(domain_path):
                if example_id == "onboard":
                    continue
                example_path = os.path.join(domain_path, example_id)
                if os.path.isdir(example_path):
                    if "result.txt" not in os.listdir(example_path):
                        # empty all files under example_id
                        for file in os.listdir(example_path):
                            os.remove(os.path.join(example_path, file))
                    else:
                        finished[domain].append(example_id)

    if not finished:
        return total_file_json

    for domain, examples in finished.items():
        if domain in total_file_json:
            total_file_json[domain] = [
                x for x in total_file_json[domain] if x not in examples
            ]

    return total_file_json


def get_result(action_space, use_model, observation_type, result_dir, total_file_json):
    target_dir = os.path.join(result_dir, action_space, observation_type, use_model)
    if not os.path.exists(target_dir):
        print("New experiment, no result yet.")
        return None

    all_result = []

    for domain in os.listdir(target_dir):
        domain_path = os.path.join(target_dir, domain)
        if os.path.isdir(domain_path):
            for example_id in os.listdir(domain_path):
                example_path = os.path.join(domain_path, example_id)
                if os.path.isdir(example_path):
                    if "result.txt" in os.listdir(example_path):
                        # empty all files under example_id
                        try:
                            all_result.append(
                                float(
                                    open(
                                        os.path.join(example_path, "result.txt"), "r"
                                    ).read()
                                )
                            )
                        except:
                            all_result.append(0.0)

    if not all_result:
        print("New experiment, no result yet.")
        return None
    else:
        print("Current Success Rate:", sum(all_result) / len(all_result) * 100, "%")
        return all_result


if __name__ == "__main__":
    ####### The complete version of the list of examples #######
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    args = config()

    with open(args.test_all_meta_path, "r", encoding="utf-8") as f:
        test_all_meta = json.load(f)

    # if args.domain != "all":
    #     test_all_meta = {args.domain: test_all_meta[args.domain]}
    #
    # test_file_list = get_unfinished(
    #     args.action_space,
    #     args.model,
    #     args.observation_type,
    #     args.result_dir,
    #     test_all_meta,
    # )
    left_info = ""
    # for domain in test_file_list:
    #     left_info += f"{domain}: {len(test_file_list[domain])}\n"
    # logger.info(f"Left tasks:\n{left_info}")

    # get_result(
    #     args.action_space,
    #     args.model,
    #     args.observation_type,
    #     args.result_dir,
    #     test_all_meta,
    # )
    test(args, test_all_meta)

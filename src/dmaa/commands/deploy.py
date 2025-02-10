import typer
from rich.console import Console
from rich.panel import Panel
from typing import Optional
# from pathlib import Path
import boto3
# from botocore.exceptions import ClientError, NoCredentialsError
# import time
import os
import json
import re
from collections import defaultdict

from dmaa.constants import MODEL_TAG_PATTERN,MODEL_DEFAULT_TAG
from dmaa.utils.aws_service_utils import get_current_region
# from dmaa.utils.aws_service_management import (
#     check_aws_environment,
#     log_pipeline_execution_details,
# )
from typing_extensions import Annotated
from dmaa.models import Model
from dmaa.models.services import Service
from dmaa.models.instances import Instance
from dmaa.models.utils.constants import InstanceType,EngineType,ServiceType
# from dmaa.utils.text_utilities import random_suffix, normalize, enum_to_choices, enum_to_strings
from dmaa.patch_questionary.select_with_help import select_with_help,Choice
from dmaa.sdk.deploy import deploy as sdk_deploy,deploy_local as sdk_deploy_local
from dmaa.sdk.deploy import parse_extra_params
from dmaa.utils.aws_service_utils import check_cn_region
import questionary
from dmaa.utils.accelerator_utils import get_gpu_num,check_cuda_exists,check_neuron_exists
from dmaa.utils.decorators import catch_aws_credential_errors,check_dmaa_env_exist,load_aws_profile
from dmaa.utils.logger_utils import make_layout
from dmaa.utils.exceptions import ModelNotSupported,ServiceNotSupported,InstanceNotSupported

app = typer.Typer()
console = Console()
layout = make_layout()

# model_instance_choices = enum_to_strings(ModelInstance)

from questionary import Style

custom_style = Style([
    ('qmark', 'fg:#66BB6A bold'),  # 问题前的标记
    ('question', 'fg:default'),     # 将问题文本颜色设置为默认颜色
    ('answer', 'fg:#4CAF50 bold'),  # 提交的答案文本
    ('pointer', 'fg:#66BB6A bold'),  # 选择提示符
    ('highlighted', 'fg:#4CAF50 bold'),  # 高亮的选项
    ('selected', 'fg:#A5D6A7 bold'),  # 选中的选项
    ('disabled', 'fg:#CED4DA italic'),  # 禁用的选项
    ('error', 'fg:#F44336 bold'),  # 错误信息
])

def show_help(choice):
    return f"{choice} (shortcut)"


def supported_models_filter(region:str,support_models:list[Model]):
    ret = []
    is_cn_region = check_cn_region(region)

    for model in support_models:
        if is_cn_region and not model.allow_china_region:
            continue
        ret.append(model)
    return ret

def supported_services_filter(region,allow_local_deploy,supported_services:list[Service]):
    ret = []
    is_cn_region = check_cn_region(region)
    for service in supported_services:
        if is_cn_region and not service.support_cn_region:
            continue
        if service.service_type == ServiceType.LOCAL and not allow_local_deploy:
            continue
        ret.append(service)
    if not ret:
        raise ServiceNotSupported(region)
    return ret

def supported_instances_filter(region,allow_local_deploy:bool,supported_instances:list[Instance]):
    ret = []
    is_cn_region = check_cn_region(region)
    for instance in supported_instances:
        if is_cn_region and not instance.support_cn_region:
            continue

        if instance.instance_type == InstanceType.LOCAL and not allow_local_deploy:
            continue
        ret.append(instance)

    if not ret:
        raise InstanceNotSupported(region)
    return ret



def check_model_support_on_cn_region(model_id,region):
    model = Model.get_model(model_id)
    is_cn_region = check_cn_region(region)
    if is_cn_region and not model.allow_china_region:
        return False
    return True

def check_service_support_on_cn_region(serivce_type, region):
    service = Service.get_service_from_service_type(serivce_type)
    is_cn_region = check_cn_region(region)
    if is_cn_region and not service.support_cn_region:
        return False
    return True

def check_instance_support_on_cn_region(instance_type, region):
    instance = Instance.get_instance_from_instance_type(instance_type)
    is_cn_region = check_cn_region(region)
    if is_cn_region and not instance.support_cn_region:
        return False
    return True

def is_valid_model_tag(name,pattern=MODEL_TAG_PATTERN):
    return bool(re.match(pattern, name))


def ask_model_id(region,model_id=None):
    if model_id is not None:
        return model_id

    # step 1: select model series name
    support_models:list[Model] = sorted(
        [Model.get_model(m) for m in Model.get_supported_models()],
        key=lambda x:x.model_series.model_series_name
    )
    # filter models
    support_models = supported_models_filter(region,support_models)

    if not support_models:
        raise ModelNotSupported(region)

    model_series_map = defaultdict(list)
    for model in support_models:
        model_series_map[model.model_series.model_series_name].append(model)

    def _get_series_description(models:list[Model]):
        model = models[0]
        description = "\n"
        description += model.model_series.description
        description += f"\nreference link: {model.model_series.reference_link}"
        description += "\nSupported models: "+ "\n - " + "\n - ".join(model.model_id for model in models)
        return description

    series_name = select_with_help(
        "Select the model series:",
        choices=[
            Choice(
                title=series_name,
                description=_get_series_description(models),
            )
            for series_name,models in model_series_map.items()
        ],
        show_description=True,
        style=custom_style
    ).ask()
    if series_name is None:
        raise typer.Exit(0)

    def _get_model_description(model:Model):
        description=f"\n\nModelType: {model.model_type}\nApplication Scenario: {model.application_scenario}"
        if model.description:
            description += f"\nDescription: {model.description}"
        return description

    # step 2 select model_id
    model_id = select_with_help(
        "Select the model name:",
        choices=[
            Choice(
                title=model.model_id,
                description=_get_model_description(model)
            )
            for model in model_series_map[series_name]
        ],
        show_description=True,
        style=custom_style
    ).ask()

    if model_id is None:
        raise typer.Exit(0)
    return model_id


#@app.callback(invoke_without_command=True)(invoke_without_command=True)
@app.callback(invoke_without_command=True)
@catch_aws_credential_errors
@check_dmaa_env_exist
@load_aws_profile
def deploy(
    model_id: Annotated[str,typer.Option("--model-id",help="Model id")
    ] = None,
    instance_type: Annotated[
        str, typer.Option("-i", "--instance-type", help="The instance type to use")
    ] = None,
    engine_type: Annotated[
        str, typer.Option("-e", "--engine-type", help="The name of the inference engine")
    ] = None,
    service_type: Annotated[
        str, typer.Option("-s", "--service-type", help="The name of the service")
    ] = None,
    framework_type:Annotated[
        str, typer.Option("--framework-type", help="The name of the framework")
    ] = None,
    model_tag: Annotated[
        str, typer.Option("--model-tag", help="give a model tag,this is useful to create multiple models with same model id")
    ] = MODEL_DEFAULT_TAG,
    extra_params: Annotated[
        str, typer.Option("--extra-params",help="extra params (Json string)")
    ] = None,
    skip_confirm: Annotated[
        Optional[bool], typer.Option("--skip-confirm", help="Skip confirmation")
    ] = False,
    force_update_env_stack:Annotated[
        Optional[bool], typer.Option("--force-update-env-stack", help="force update env stack")
    ] = False,
    allow_local_deploy:Annotated[
        Optional[bool], typer.Option("--allow-local-deploy", help="allow local instance")
    ] = False,

):
    # console.print("[bold blue]Checking AWS environment...[/bold blue]")

    region = get_current_region()

    # ask model id
    model_id = ask_model_id(region,model_id=model_id)

    if not check_model_support_on_cn_region(model_id,region):
        raise ModelNotSupported(region,model_id=model_id)


    model = Model.get_model(model_id)
    # support services
    supported_services:list[Service] = model.supported_services
    supported_services = supported_services_filter(region,allow_local_deploy,supported_services)
    if service_type is None:
        if len(supported_services) > 1:
            service_name = select_with_help(
                "Select the service for deployment:",
                choices=[
                    Choice(
                        title=service.name,
                        description=service.description
                    )
                    for service in supported_services
                ],
                style=custom_style
            ).ask()
            service_type = Service.get_service_from_name(service_name).service_type
        else:
            service_type = supported_services[0].service_type
            console.print(f"[bold blue]service type: {supported_services[0].name}[/bold blue]")
    else:
        supported_service_types = model.supported_service_types
        console.print(f"[bold blue]service type: {service_type}[/bold blue]")
        assert service_type in supported_service_types, \
            f"Invalid service type: {service_type}, supported service types for model: {model_id}: {supported_service_types}"

    if service_type is None:
        raise typer.Exit(0)

    if not check_service_support_on_cn_region(service_type,region):
        raise ServiceNotSupported(region, service_type=service_type)

    #

    # support instance
    supported_instances = model.supported_instances
    supported_instances = supported_instances_filter(region,allow_local_deploy,supported_instances)
    if service_type == ServiceType.LOCAL:
        if check_cuda_exists():
            if os.environ.get('CUDA_VISIBLE_DEVICES'):
                console.print(f"[bold blue]local gpus: {os.environ.get('CUDA_VISIBLE_DEVICES')}[/bold blue]")
            else:
                gpu_num = get_gpu_num()
                support_gpu_num = supported_instances[0].gpu_num
                default_gpus_str = ",".join([str(i) for i in range(min(gpu_num,support_gpu_num))])
                gpus_to_deploy = questionary.text(
                        "input the local gpu ids to deploy the model (e.g. 0,1,2):",
                        default=f"{default_gpus_str}"
                    ).ask()
                os.environ['CUDA_VISIBLE_DEVICES']=gpus_to_deploy
        instance_type = InstanceType.LOCAL
    else:
        if instance_type is None:
            if len(supported_instances)>1:
                instance_type = select_with_help(
                    "Select the instance type:",
                    choices=[
                        Choice(
                            title=instance.instance_type,
                            description=instance.description,
                        )
                        for instance in supported_instances
                    ],
                    style=custom_style
                ).ask()
            else:
                instance_type = supported_instances[0].instance_type
                console.print(f"[bold blue]instance type: {instance_type}[/bold blue]")

        else:
            supported_instance_types = model.supported_instance_types
            console.print(f"[bold blue]instance type: {instance_type}[/bold blue]")
            assert instance_type in supported_instance_types,\
                    f"Invalid instance type: {instance_type}, supoorted instance types for model: {model_id}: {supported_instance_types}"

    if instance_type is None:
        raise typer.Exit(0)

    if not check_instance_support_on_cn_region(instance_type,region):
        raise InstanceNotSupported(region, instance_type=instance_type)

    supported_engines = model.supported_engines
    if Instance.check_inf2_instance(instance_type):
        supported_engines = [engine for engine in supported_engines if engine.support_inf2_instance]
    # filter engines that unsupported on selected instance type
    # supported_engines = [engine for engine in supported_engines if instance_type in engine.supported_instance_types]

    if engine_type is None:
        if len(supported_engines)>1:
            engine_type = select_with_help(
                "Select the inference engine to use:",
                choices=[
                    Choice(
                        title=engine.engine_type,
                        description=engine.description
                    )
                    for engine in supported_engines
                ],
                style=custom_style
            ).ask()
        else:
            engine_type = supported_engines[0].engine_type
            console.print(f"[bold blue]engine type: {engine_type}[/bold blue]")
    else:
        supported_engine_types = model.supported_engine_types
        console.print(f"[bold blue]engine type: {engine_type}[/bold blue]")
        assert engine_type in supported_engine_types,\
                f"Invalid engine type: {engine_type}, supported engine types for model: {model_id}: {supported_engine_types}"

    if engine_type is None:
        raise typer.Exit(0)

    # framework
    supported_frameworks = model.supported_frameworks
    if framework_type is None:
        if len(supported_frameworks)>1:
            framework_type = select_with_help(
                "Select the inference engine to use:",
                choices=[
                    Choice(
                        title=framework.framework_type,
                        description=framework.description
                    )
                    for framework in supported_frameworks
                ],
                style=custom_style
            ).ask()
        else:
            framework_type = supported_frameworks[0].framework_type
            console.print(f"[bold blue]framework type: {framework_type}[/bold blue]")
    else:
        supported_framework_types = model.supported_framework_types
        console.print(f"[bold blue]framework type: {framework_type}[/bold blue]")
        assert framework_type in supported_framework_types,\
                f"Invalid engine type: {framework_type}, supported framwork types for model: {model_id}: {supported_framework_types}"

    if framework_type is None:
        raise typer.Exit(0)

    # extra_params
    if extra_params is None:
        while True:
            extra_params = questionary.text(
                "(Optional) Additional deployment parameters (JSON string or local file path), you can skip by pressing Enter:",
                default="{}"
            ).ask()

            try:
                extra_params = parse_extra_params(extra_params)
                break
            except json.JSONDecodeError as e:
                console.print("[red]Invalid JSON format. Please try again.[/red]")
    else:
        try:
            extra_params = parse_extra_params(extra_params)
        except json.JSONDecodeError as e:
            console.print("[red]Invalid JSON format. Please try again.[/red]")

    # model tag
    if model_tag==MODEL_DEFAULT_TAG and not skip_confirm and not service_type == ServiceType.LOCAL:
        while True:
            model_tag = questionary.text(
                    "(Optional) Add a model deployment tag (custom label), you can skip by pressing Enter:",
                    default=""
                ).ask()
            if model_tag == MODEL_DEFAULT_TAG:
                console.print(f"[bold blue]invalid model tag: {model_tag}. Please try again.[/bold blue]")
            else:
                console.print(f"[bold blue] model tag: {model_tag}[/bold blue]")
                break
            if not model_tag and not is_valid_model_tag(model_tag):
                console.print(f"[bold blue]invalid model tag: {model_tag}. Please ensure that the tag complies with the standard rules: {MODEL_TAG_PATTERN}.[/bold blue]")

    if model_tag == "":
        model_tag = MODEL_DEFAULT_TAG

    if not skip_confirm:
        if not typer.confirm(
            "Would you like to proceed with the deployment? Please verify your selections above.",
            abort=True,
        ):
            raise typer.Exit(0)
    # Start pipeline execution
    if service_type != ServiceType.LOCAL:
        response = sdk_deploy(
            model_id=model_id,
            instance_type=instance_type,
            engine_type=engine_type,
            service_type=service_type,
            region=region,
            extra_params = extra_params,
            model_tag=model_tag,
            env_stack_on_failure = "ROLLBACK",
            force_env_stack_update = force_update_env_stack,
            waiting_until_deploy_complete=True
        )
        console.print(f"[bold green]Model deployment pipeline execution initiated. Execution ID: {response['pipeline_execution_id']}[/bold green]")
    else:
        response = sdk_deploy_local(
            model_id=model_id,
            instance_type=instance_type,
            engine_type=engine_type,
            service_type=service_type,
            model_tag=MODEL_DEFAULT_TAG,
            # region=region,
            extra_params = extra_params
        )
    return response

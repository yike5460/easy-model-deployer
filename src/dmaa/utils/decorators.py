from functools import wraps
from botocore.exceptions import ClientError, NoCredentialsError
from rich.console import Console
from rich.panel import Panel
from .logger_utils import get_logger
import traceback
import typer
import boto3
import os
from dmaa.constants import ENV_STACK_NAME
from dmaa.utils.aws_service_utils import get_current_region
# from dmaa.patch_questionary.select_with_help import ,Choice
from dmaa.utils.profile_manager import profile_manager


logger =  get_logger(__name__)

def catch_aws_credential_errors(fn):
    @wraps(fn)
    def inner(*args,**kwargs):
        try:
            return fn(*args, **kwargs)
        except (NoCredentialsError,):
            logger.error(traceback.format_exc())
            console = Console()
            console.print("[red]Error: AWS credentials not found or invalid.[/red]")
            console.print("Please configure your AWS credentials using:")
            console.print("  `aws configure`")
            raise
    return inner

def check_dmaa_env_exist(fn):
    @wraps(fn)
    def inner(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except ClientError as e:
            logger.error(traceback.format_exc())
            console = Console()
            if "does not exist" in str(e) and ENV_STACK_NAME in str(e):
                console.print("[yellow]Infrastructure not bootstrapped.[/yellow]")
                console.print(
                    "Please run 'dmaa bootstrap' first to set up required AWS resources."
                )
            raise typer.Exit(1)
    return inner

# def select_aws_profile(fn):
#     @wraps(fn)
#     def wrapper(*args, **kwargs):
#         custom_style = Style([
#             ('qmark', 'fg:#66BB6A bold'),  # 问题前的标记
#             ('question', 'fg:default'),     # 将问题文本颜色设置为默认颜色
#             ('answer', 'fg:#4CAF50 bold'),  # 提交的答案文本
#             ('pointer', 'fg:#66BB6A bold'),  # 选择提示符
#             ('highlighted', 'fg:#4CAF50 bold'),  # 高亮的选项
#             ('selected', 'fg:#A5D6A7 bold'),  # 选中的选项
#             ('disabled', 'fg:#CED4DA italic'),  # 禁用的选项
#             ('error', 'fg:#F44336 bold'),  # 错误信息
#         ])
#         console = Console()
#         session = boto3.Session()
#         profiles = session.available_profiles
#         console.print("Available AWS profiles:")
#         if profiles:
#             if len(profiles) > 1:
#                 choices = []
#                 for profile_name in profiles:
#                     session = boto3.Session(profile_name=profile_name)
#                     region = session.region_name
#                     choices.append(
#                         Choice(
#                             title=profile_name,
#                             description=f"ProfileName: {profile_name}, Region: {region}"
#                         )
#                     )
#                 choices.append(Choice(title="Not listed", description="Manually enter the AK/SK"))
#                 selected_profile_name = select_with_help(
#                     "Select the profile for deployment:",
#                     choices=choices,
#                     style=custom_style
#                 ).ask()
#             else:
#                 selected_profile_name = profiles[0]
#                 console.print(f"[bold blue]Current profile: {selected_profile_name}[/bold blue]")
#             if selected_profile_name != "Not listed":
#                 os.environ["AWS_PROFILE"] = selected_profile_name
#                 with open("/tmp/aws_profile", "w") as f:
#                     f.write(selected_profile_name)
#             else:
#                 if os.path.exists("/tmp/aws_profile"):
#                     os.remove("/tmp/aws_profile")
#         return fn(*args, **kwargs)
#     return wrapper


@catch_aws_credential_errors
def print_aws_profile():
    console = Console()
    sts = boto3.client("sts")
    response = sts.get_caller_identity()
    profile_name = os.environ.get("AWS_PROFILE","default")
    account_id = response["Account"]
    region = get_current_region()
    if region is None:
        console.print("[red]Error: Unable to determine AWS region.[/red]")
        raise typer.Exit(1)
    console.print(Panel.fit(
        f"[bold green]Account ID:[/bold green] {account_id}\n"
        f"[bold green]Region    :[/bold green] {region}\n"
        f"[bold green]Profile   :[/bold green] {profile_name}",
        title="[bold blue]AWS Configuration[/bold blue]",
        border_style="blue"
    ))



def load_aws_profile(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        # profile_name = None
        # try:
        #     profile_name = profile_manager.load_profile_name_from_local()
        # except FileNotFoundError:
        #     pass
        # except Exception as e:
        #     logger.error(f"Error loading AWS profile: {str(e)}")

        # if profile_name:
        #     os.environ["AWS_PROFILE"] = profile_name

        print_aws_profile()
        # try:
        #     sts = boto3.client("sts")
        #     response = sts.get_caller_identity()
        #     profile_name = os.environ.get("AWS_PROFILE")
        #     account_id = response["Account"]
        #     region = get_current_region()
        #     if region is None:
        #         console.print("[red]Error: Unable to determine AWS region.[/red]")
        #         raise typer.Exit(1)
        #     console.print(f"AWS Account: {account_id}\nAWS Region: {region}\n AWS Profile: {profile_name}")
        # except (ClientError, NoCredentialsError):
        #     console.print("[red]Error: AWS credentials not found or invalid.[/red]")
        #     console.print("Please configure your AWS credentials using:")
        #     console.print("  `aws configure`")
        #     raise typer.Exit(1)
        return fn(*args, **kwargs)
    return wrapper

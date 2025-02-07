import os
import subprocess
import logging
import argparse
import json
from jinja2 import Template
import boto3
from dmaa.models import (
    Model,
    ExecutableConfig, 
)
from dmaa.models.utils.constants import (
    ServiceType, 
    EngineType, 
    FrameworkType,
    InstanceType,
)
from dmaa.models.utils.serialize_utils import load_extra_params, dump_extra_params
from dmaa.constants import MODEL_DEFAULT_TAG
from dmaa.utils.aws_service_utils import check_cn_region

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

parser = argparse.ArgumentParser()
parser.add_argument("--region", type=str, default=os.environ.get("region", "us-east-1"))
parser.add_argument(
    "--model_id",
    type=str,
    default=os.environ.get("model_id", None),
    # default="Qwen/Qwen2-beta-7B-Chat",
    help="Currently supports Qwen/Qwen2-beta-7B-Chat & Qwen/Qwen2.5-72B-Instruct-AWQ",
)
# parser.add_argument("--model_type", type=str, default="chat")
parser.add_argument(
    "--backend_type", type=str, default=os.environ.get("backend_type", EngineType.VLLM)
)
parser.add_argument(
    "--service_type",
    type=str,
    default=os.environ.get("service_type", ServiceType.SAGEMAKER),
)
parser.add_argument(
    "--framework_type",
    type=str,
    default=os.environ.get("framework_type", FrameworkType.FASTAPI),
)
parser.add_argument("--image_name", type=str, default=os.environ.get("image_name", ""))
parser.add_argument(
    "--image_tag", type=str, default=os.environ.get("image_tag", "latest")
)
# parser.add_argument("--gpu_num", type=int, default=1)
parser.add_argument(
    "--model_s3_bucket",
    type=str,
    default=os.environ.get("model_s3_bucket", "dmaa-us-east-1-bucket-1234567890"),
)
parser.add_argument(
    "--instance_type", type=str, default=os.environ.get("instance_type", "g5.2xlarge")
)
parser.add_argument(
    "--extra_params",
    type=load_extra_params,
    default=os.environ.get("extra_params", "{}"),
)


args = parser.parse_known_args()[0]
logger.info(f"build image args: {vars(args)}")

# User defined variables
region = args.region
model_id = args.model_id
# model_type = args.model_type
backend_type = args.backend_type
# gpu_num = args.gpu_num
model_s3_bucket = args.model_s3_bucket
instance_type = args.instance_type
service_type = args.service_type
framework_type = args.framework_type
extra_params = args.extra_params

iamge_tag = args.image_tag  # change as needed
image_name = args.image_name  # change as needed


def run(
    region,
    model_id,
    model_tag,
    backend_type,
    service_type,
    framework_type,
    image_name,
    image_tag,
    model_s3_bucket,
    instance_type,
    extra_params
):
    model = Model.get_model(model_id)
    current_engine = model.find_current_engine(backend_type)
    executable_config = ExecutableConfig(
        region=region,
        current_engine=current_engine,
        current_instance=model.find_current_instance(instance_type),
        current_service=model.find_current_service(service_type),
        current_framework=model.find_current_framework(framework_type),
        # gpu_num=gpu_num,
        model_s3_bucket=model_s3_bucket,
        extra_params=extra_params,
        model_tag=model_tag,
    )
    execute_model = model.convert_to_execute_model(executable_config)

    # engine = execute_model.get_engine()
    logger.info(f"Building and deploying {model_id} on {backend_type} backend")
    # Write Dockerfile
    logger.info(f"Write docker serving script for {backend_type} backend")
    logger.info(f"Write Dockerfile for {backend_type} backend")
    engine_docker_file_path = execute_model.get_dockerfile()
    execute_dir = execute_model.get_execute_dir()

    os.makedirs(execute_dir, exist_ok=True)
    # assert os.system(f"rm -rf {execute_dir}/*") == 0

    # find dmaa path
    dmaa_path_in_pipeline = os.path.join(os.getcwd(), "dmaa")
    if os.path.exists(dmaa_path_in_pipeline):
        # print('copy models',f"cp -r models {execute_dir}")
        assert os.system(f"cp -Lr {dmaa_path_in_pipeline} {execute_dir}") == 0
    else:
        raise RuntimeError("dmaa path not found...")
    # elif os.path.exists(os.path.join(parent_dir,"models")):
    #     # print(f"cp -r {os.path.join(parent_dir,'models')} {execute_dir}")
    #     assert os.system(f"cp -r {os.path.join(parent_dir,'models')} {execute_dir}/dmaa") == 0

    # find models path
    # model_path_in_pipeline = os.path.join("dmaa","models")
    # if os.path.exists(model_path_in_pipeline) and not os.path.islink(model_path_in_pipeline):
    #     # print('copy models',f"cp -r models {execute_dir}")
    #     assert os.system(f"cp -r {model_path_in_pipeline} {execute_dir}/dmaa") == 0
    # elif os.path.exists(os.path.join(parent_dir,"models")):
    #     # print(f"cp -r {os.path.join(parent_dir,'models')} {execute_dir}")
    #     assert os.system(f"cp -r {os.path.join(parent_dir,'models')} {execute_dir}/dmaa") == 0

    assert os.system(f"cp -r backend {execute_dir}") == 0
    assert os.system(f"cp -r utils {execute_dir}") == 0

    # download s5cmd
    # assert os.system('curl https://github.com/peak/s5cmd/releases/download/v2.0.0/s5cmd_2.0.0_Linux-64bit.tar.gz -L -o /tmp/s5cmd.tar.gz') == 0
    # assert os.system("mkdir -p /tmp/s5cmd && tar -xvf /tmp/s5cmd.tar.gz -C /tmp/s5cmd") == 0
    assert os.system(f"cp s5cmd {execute_dir}") == 0
    assert os.system(f"cp framework/fast_api/fast_api.py {execute_dir}") == 0
    # assert os.system(f"cp deploy/build_and_push_image.sh {execute_dir}") == 0
    # assert os.system(f"cp -r {execute_model.get_engine_dir()}/* {execute_dir}") == 0

    # write execute dockerfile
    dockerfile_name = execute_model.executable_config.current_engine.dockerfile_name
    with open(f"{execute_dir}/{dockerfile_name}", "w") as framework_f:
        with open(engine_docker_file_path) as engine_f:
            engine_dockerfile_template = Template(engine_f.read())
        engine_dockerfile = engine_dockerfile_template.render(
            **execute_model.executable_config.current_engine.engine_dockerfile_config,
            REGION=region,
        )
        framework_f.write(engine_dockerfile)
        framework_f.write("\n")
        if (
            execute_model.executable_config.current_engine.engine_type
            == EngineType.COMFYUI
        ):
            framework_f.write("COPY ./ /home/ubuntu/")
        else:
            framework_f.write("COPY ./ /opt/ml/code/")
        framework_f.write("\n")
        framework_f.write("COPY s5cmd /app/s5cmd")
        framework_f.write("\n")
        if (
            execute_model.executable_config.current_framework.framework_type
            == FrameworkType.FASTAPI
        ):
            # extra_params_commands = ""
            # default_extra_params = execute_model.default_extra_params or {}
            # logger.info(f"default_extra_params: {default_extra_params}")
            # extra_params_new = {**extra_params,**default_extra_params}
            # TODO: filter vllm params
            engine_params = extra_params.get("engine_param", {})
            extra_params_commands = dump_extra_params(engine_params)
            # for k,v in engine_params.items():
            #     extra_params_commands += f' --{k} "{v}"'

            fastapi_serve_command = (
                f"export AWS_DEFAULT_REGION={region} && "
                f"export PYTHONPATH=.:$PYTHONPATH && "
                f"python3 fast_api.py"
                f" --backend_type={backend_type}"
                f" --model_id={model_id}"
                f" --model_s3_bucket={model_s3_bucket}"
                f" --instance_type={instance_type}"
                f" --service_type={service_type}"
                f' --engine_params "{extra_params_commands}"'
                f" --port 8080"
            )
            logger.info(f"fastapi_serve_command: {fastapi_serve_command}")
            framework_f.write("\n")
            framework_f.write(f"ENTRYPOINT {fastapi_serve_command}")

    # Build and push image
    logger.info(f"Building and pushing {image_name} image")

    # docker build image
    # get current aws account_id
    push_image_account_id = execute_model.get_image_push_account_id()
    build_image_account_id = (
        execute_model.executable_config.current_engine.base_image_account_id
    )
    build_image_host = execute_model.executable_config.current_engine.base_image_host

    # get ecr repo uri
    ecr_repo_uri = execute_model.get_image_uri(
        account_id=push_image_account_id,
        region=region,
        image_name=image_name,
        image_tag=image_tag,
    )

    print("build_image_account_id", build_image_account_id, push_image_account_id)

    if not build_image_host and build_image_account_id:
        build_image_host = execute_model.get_image_host(
            execute_model.get_image_uri(
                account_id=build_image_account_id,
                region=region,
                image_name=image_name,
                image_tag=image_tag,
            )
        )

    push_image_host = execute_model.get_image_host(ecr_repo_uri)

    # build image
    use_public_ecr = execute_model.executable_config.current_engine.use_public_ecr
    if use_public_ecr:
        ecr_name = "ecr-public"
    else:
        ecr_name = "ecr"

    docker_login_region = (
        execute_model.executable_config.current_engine.docker_login_region
    )

    docker_login_region = docker_login_region or region

    if build_image_host:
        if check_cn_region(region):
            build_image_script = (
                f"cd {execute_dir}"
                f' && docker build --platform linux/amd64 -f {dockerfile_name} -t "{ecr_repo_uri}" .'
            )
        else:
            build_image_script = (
                f"cd {execute_dir}"
                f" && aws {ecr_name} get-login-password --region {docker_login_region} | docker login --username AWS --password-stdin {build_image_host}"
                f' && docker build --platform linux/amd64 -f {dockerfile_name} -t "{ecr_repo_uri}" .'
            )
        # build_image_script = (
        #     f"cd {execute_dir}"
        #     f" && aws {ecr_name} get-login-password --region {docker_login_region} | docker login --username AWS --password-stdin {build_image_host}"
        #     f' && docker build --platform linux/amd64 -f {dockerfile_name} -t "{ecr_repo_uri}" .'
        # )
    else:
        build_image_script = (
            f"cd {execute_dir}"
            f' && docker build --platform linux/amd64 -f {dockerfile_name} -t "{ecr_repo_uri}" .'
        )

    logger.info(f"building image: {build_image_script}")
    assert os.system(build_image_script) == 0

    # push image
    # It should not push the image to ecr when service_type is `local`
    if service_type != ServiceType.LOCAL:
        ecr_client = boto3.client("ecr", region_name=region)
        try:
            response = ecr_client.create_repository(
                repositoryName=image_name,
            )
            logger.info(f"ecr repo: {image_name} created.")
        except ecr_client.exceptions.RepositoryAlreadyExistsException:
            logger.info(f"ecr repo: {image_name} exist.")

        ##  give erc repo policy
        ecr_repository_policy = {
            "Version": "2008-10-17",
            "Statement": [
                {
                    "Sid": "new statement",
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": [
                        "ecr: CompleteLayerUpload",
                        "ecr: InitiateLayerUpload",
                        "ecr: ListImages",
                        "ecr:BatchCheckLayerAvailability",
                        "ecr:BatchGetImage",
                        "ecr:DescribeImages",
                        "ecr:DescribeRepositories",
                        "ecr:GetDownloadUrlForLayer",
                    ],
                }
            ],
        }
        response = ecr_client.set_repository_policy(
            repositoryName=image_name, policyText=json.dumps(ecr_repository_policy)
        )

        ## push image
        push_image_script = (
            f"cd {execute_dir}"
            f" && aws ecr get-login-password --region {region} | docker login --username AWS --password-stdin {push_image_host}"
            f' && docker push "{ecr_repo_uri}"'
        )

        logger.info(f"pushing image: {push_image_script}")
        assert os.system(push_image_script) == 0

    image_uri = ecr_repo_uri
    logger.info(f"Image URI: {ecr_repo_uri}")

    parameters = {"ecr_repo_uri": ecr_repo_uri}
    return parameters

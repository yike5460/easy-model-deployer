from .revision import VERSION, convert_version_name_to_stack_name
VERSION_MODIFY = convert_version_name_to_stack_name(VERSION)
ENV_STACK_NAME = f'EMD-Env-{VERSION_MODIFY}'
MODEL_STACK_NAME_PREFIX = f"EMD-Model"
ENV_BUCKET_NAME_PREFIX = "emd-env-artifactbucket"
CODEPIPELINE_NAME = f"{ENV_STACK_NAME}-Pipeline"
CODEBUILD_ROLE_NAME_TEMPLATE = f"{ENV_STACK_NAME}-CodeBuildRole-{{region}}"
CODEPIPELINE_ROLE_NAME_TEMPLATE = f"{ENV_STACK_NAME}-CodePipelineRole-{{region}}"
CLOUDFORMATION_ROLE_NAME_TEMPLATE = f"{ENV_STACK_NAME}-CloudFormationRole-{{region}}"

STACK_COMPLATE_STATUS_LIST = ['CREATE_COMPLETE','UPDATE_COMPLETE']
EMD_STACK_NOT_EXISTS_STATUS = 'NOT_EXISTS'
EMD_STACK_OK_STATUS = 'OK'
EMD_STACK_NOT_WORKING_STATUS = 'NOT_WORKING'

MODEL_DEFAULT_TAG = "dev"

EMD_MODELS_LOCAL_DIR_TEMPLATE = "emd_models/{model_id}"
EMD_MODELS_S3_KEY_TEMPLATE = EMD_MODELS_LOCAL_DIR_TEMPLATE

EMD_DEFAULT_PROFILE_PARH = "~/.emd_default_profile"

EMD_DEFAULT_CONTAINER_PREFIX = "emd"

MODEL_TAG_PATTERN = r'^[a-z0-9]([a-z0-9-_]{0,61}[a-z0-9])?$'

LOCAL_REGION = "local"
# EMD_USE_NO_PROFILE_CHOICE = "Don't set"

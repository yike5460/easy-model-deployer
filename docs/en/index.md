<h3 align="center">
Easy Model Deployer - Simple, Efficient, and Easy-to-Integrate
</h3>

---

*Latest News* 🔥

- [2025/03] We officially released EMD!

---

## About

EMD (Easy Model Deployer) is a lightweight tool designed to simplify model deployment. Built for developers who need reliable and scalable model serving without complex setup.

**Key Features**
- One-click deployment of models to the cloud (Amazon SageMaker, Amazon ECS, Amazon EC2)
- Diverse model types (LLMs, VLMs, Embeddings, Vision, etc.)
- Rich inference engine (vLLM, TGI, Lmdeploy, etc.)
- Different instance types (CPU/GPU/AWS Inferentia)
- Convenient integration (OpenAI Compatible API, LangChain client, etc.)

**Notes**

- Please check the [Supported Models](docs/en/supported_models.md) for complete list.
- OpenAI Compatible API is supported only for Amazon ECS and Amazon EC2 deployment.

## Getting Started

### Installation

Install EMD with `pip`, currently only support for Python 3.9 and above:

```bash
curl  https://github.com/aws-samples/easy-model-deployer/releases/download/dev/emd-0.6.0-py3-none-any.whl -o emd-0.6.0-py3-none-any.whl && pip install emd-0.6.0-py3-none-any.whl"[all]"
```

Visit our [documentation](https://aws-samples.github.io/easy-model-deployer/) to learn more.

### Usage

#### Choose your default aws profile.
```bash
emd config set-default-profile-name
```
Notes: If you don't set aws profile, it will use the default profile in your env (suitable for Temporary Credentials). Whenever you want to switch deployment accounts, run ```emd config set-default-profile-name```
![alt text](docs/images/emd-config.png)

#### Bootstrap emd stack
```bash
emd bootstrap
```
Notes: This is going to set up the necessary resources for model deployment. Whenever you change EMD version, run this command again.
![alt text](docs/images/emd-bootstrap.png)

#### Choose deployment parameters interactively by ```emd deploy``` or deploy with one command
```bash
emd deploy --model-id DeepSeek-R1-Distill-Qwen-1.5B --instance-type g5.8xlarge --engine-type vllm --framework-type fastapi --service-type sagemaker --extra-params {} --skip-confirm
```
Notes: Get complete parameters by ```emd deploy --help``` and find the values of the required parameters [here](docs/en/supported_models.md)
When you see "Waiting for model: ...",  it means the deployment task has started, you can quit the current task by ctrl+c.
![alt text](docs/images/emd-deploy.png)

#### Check deployment status.
```bash
emd status
```
![alt text](docs/images/emd-status.png)
Notes: EMD allows to launch multiple deployment tasks at the same time.

=======
---

*Latest News* 🔥

- [2025/03] We officially released EMD! Check out our [blog post](https://vllm.ai).

---

## About

EMD (Easy Model Deployer) is a lightweight tool designed to simplify model deployment. Built for developers who need reliable and scalable model serving without complex setup.

**Key Features**
- One-click deployment of models to the cloud (Amazon SageMaker, Amazon ECS) or on-premises
- Diverse model types (LLMs, VLMs, Embeddings, Vision, etc.)
- Rich inference engine (vLLM, TGI, Lmdeploy, etc.)
- Different instance types (CPU/GPU/AWS Inferentia)
- Convenient integration (OpenAI Compatible API, LangChain client, etc.)

**Notes**

- Please check the [Supported Models](docs/supported_models.md) for complete list.
- OpenAI Compatible API is supported only for Amazon ECS deployment.

## Getting Started

### Installation

Install EMD with `pip`, currently only support for Python 3.9 and above:

```bash
curl  https://github.com/aws-samples/easy-model-deployer/releases/download/dev/emd-0.6.0-py3-none-any.whl -o emd-0.6.0-py3-none-any.whl && pip install emd-0.6.0-py3-none-any.whl"[all]"
```

Visit our [documentation](https://aws-samples.github.io/easy-model-deployer/) to learn more.

### Usage

#### Choose your default aws profile.
```bash
emd config set-default-profile-name
```
Notes: If you don't set aws profile, it will use the default profile in your env (suitable for Temporary Credentials). Whenever you want to switch deployment accounts, run ```emd config set-default-profile-name```
![alt text](docs/images/emd-config.png)

#### Bootstrap emd stack
```bash
emd bootstrap
```
Notes: This is going to set up the necessary resources for model deployment. Whenever you change EMD version, run this command again.
![alt text](docs/images/emd-bootstrap.png)

#### Choose deployment parameters interactively by ```emd deploy``` or deploy with one command
```bash
emd deploy --model-id DeepSeek-R1-Distill-Qwen-1.5B --instance-type g5.8xlarge --engine-type vllm --framework-type fastapi --service-type sagemaker --extra-params {} --skip-confirm
```
Notes: Get complete parameters by ```emd deploy --help``` and find the values of the required parameters [here](docs/en/supported_models.md)
When you see "Waiting for model: ...",  it means the deployment task has started, you can quit the current task by ctrl+c.
![alt text](docs/images/emd-deploy.png)

#### Check deployment status.
```bash
emd status
```
![alt text](docs/images/emd-status.png)
Notes: EMD allows to launch multiple deployment tasks at the same time.

#### Quick functional verfication or check our [documentation](https://aws-samples.github.io/easy-model-deployer/) for integration examples.
```bash
emd invoke DeepSeek-R1-Distill-Qwen-1.5B
```
Notes: Find *ModelId* in the output of ```emd status```.
![alt text](docs/images/emd-invoke.png)

#### Delete the deployed model
```bash
emd destroy DeepSeek-R1-Distill-Qwen-1.5B
```
Notes: Find *ModelId* in the output of ```emd status```.
![alt text](docs/images/emd-destroy.png)



## Documentation

For advanced configurations and detailed guides, visit our [documentation site](https://aws-samples.github.io/easy-model-deployer/).


## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

# great-expectations==0.14.0
from os import path
from typing import Dict, List

import boto3
import yaml
from great_expectations.checkpoint import Checkpoint
from great_expectations.core.batch import RuntimeBatchRequest
from great_expectations.data_context import BaseDataContext

# from great_expectations.data_context.store import TupleFilesystemStoreBackend
from great_expectations.data_context.types.base import (  # FilesystemStoreBackendDefaults,
    DataContextConfig,
)
from great_expectations.validator.validator import Validator


# TODO add kwargs ge methods
def load_yaml(filename: str) -> Dict[str, Dict]:
    """Loads a YAML configuration file from s3"""
    if filename.startswith("s3://"):
        path_file = filename.split("//")[1].split("/")
        bucket = path_file.pop(0)
        file = "/".join(path_file)

        s3 = boto3.resource("s3")
        obj = s3.Object(bucket, file)
        data: Dict[str, Dict] = yaml.load(obj.get()["Body"], Loader=yaml.SafeLoader)

    elif path.exists(filename):
        with open(filename, "r") as f:
            data = yaml.load(f, Loader=yaml.FullLoader)
    else:
        raise Exception(f"File does not exist: {filename}")

    return data


def get_context(config: Dict, **kwargs) -> BaseDataContext:
    context = BaseDataContext(
        project_config=DataContextConfig(
            **config,
            **kwargs,
            # store_backend_defaults=FilesystemStoreBackendDefaults(
            #     root_directory="optional/absolute/path/for/stores"
            # ),
        )
    )
    return context


def get_batch_request(
    df, datasource_name: str, data_asset_name: str
) -> RuntimeBatchRequest:

    if datasource_name.startswith("spark"):
        batch_identifiers = {"batch_id": "default_identifier"}
    else:
        batch_identifiers = {"default_identifier_name": "default_identifier"}

    # Here is a RuntimeBatchRequest using a dataframe
    batch_request = RuntimeBatchRequest(
        datasource_name=datasource_name,
        data_connector_name="default_runtime_data_connector_name",
        data_asset_name=data_asset_name,  # This can be anything that identifies this data_asset for you
        batch_identifiers=batch_identifiers,
        runtime_parameters={"batch_data": df},  # Your dataframe goes here
    )

    return batch_request


def init_validator(
    context: BaseDataContext,
    batch_request: RuntimeBatchRequest,
    expectation_suite_name: str,
    create_expectation_suite: bool = False,
    overwrite_existing=False,
) -> Validator:
    if create_expectation_suite:
        context.create_expectation_suite(
            expectation_suite_name=expectation_suite_name,
            overwrite_existing=overwrite_existing,
        )

    validator = context.get_validator(
        batch_request=batch_request, expectation_suite_name=expectation_suite_name
    )

    return validator


def run_checkpoint(
    context: DataContextConfig,
    checkpoint_name: str,
    expectation_suite_name: str,
    run_id: str,
    batch_request: RuntimeBatchRequest,
    action_list: List,
    open_data_docs: bool = False,
):
    checkpoint_config = {
        "config_version": 1.0,
        "class_name": "Checkpoint",
        "run_name_template": f"%Y-%M-{checkpoint_name}",
        "validations": [
            {
                "batch_request": batch_request,
                "expectation_suite_name": expectation_suite_name,
                "action_list": action_list,
            }
        ],
    }

    checkpoint = Checkpoint(
        name=checkpoint_name, data_context=context, **checkpoint_config
    )

    checkpoint_result = checkpoint.run(run_name=f"{run_id}-{checkpoint_name}")

    if open_data_docs:
        context.open_data_docs()

    return checkpoint_result

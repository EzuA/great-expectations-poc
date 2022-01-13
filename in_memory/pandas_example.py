# great-expectations==0.14.0
import json
import logging

import jinja2
import pandas as pd

from in_memory.helpers import (
    get_batch_request,
    get_context,
    init_validator,
    load_yaml,
    run_checkpoint,
)

logger = logging.getLogger(__name__)

# Constants
DATASOURCE_NAME = "pandas_datasource"
ROOT_PREFIX = "great_expectations"
EXPECTATIONS_STORE_PREFIX = f"{ROOT_PREFIX}/expectations"
VALIDATIONS_STORE_PREFIX = f"{ROOT_PREFIX}/validations"
CHECKPOINTS_STORE_PREFIX = f"{ROOT_PREFIX}/checkpoints"
S3_SITE_STORE_PREFIX = f"{ROOT_PREFIX}/data_docs"
S3_BUCKET = "kavak-data-temp-dev"
CHECKPOINT_NAME = "my_pandas_checkpoint"
EXPECTATION_SUITE_NAME = "example_pandas_expectations"
RUN_ID = "airflow_run_id"
DATA_ASSET_NAME = "pandas_example"
# PATH_CONTEXT_FILE = f"s3://{S3_BUCKET}/{ROOT_PREFIX}/great_expectations.yml"
PATH_CONTEXT_FILE = "./in_memory/great_expectations.yml"

config = json.dumps(load_yaml(filename=PATH_CONTEXT_FILE))
config = jinja2.Template(config).render(
    BUCKET_NAME=S3_BUCKET,
    EXPECTATIONS_STORE_PREFIX=EXPECTATIONS_STORE_PREFIX,
    VALIDATIONS_STORE_PREFIX=VALIDATIONS_STORE_PREFIX,
    CHECKPOINTS_STORE_PREFIX=CHECKPOINTS_STORE_PREFIX,
    S3_SITE_STORE_PREFIX=S3_SITE_STORE_PREFIX,
)
config_dict = json.loads(config)

logger.info("Context init")
context = get_context(
    config=config_dict, plugins_directory=None, config_variables_file_path=None,
)

# Use dataframe for creating expectations
logger.info("Creating dataframe")

df = pd.DataFrame(
    [[1, 2, 3], [4, 5, 6], [7, 8, 9], [10, 11, 1]], columns=["col_a", "col_b", "col_c"]
)

# Generate a batch of data
batch_request = get_batch_request(
    df, datasource_name=DATASOURCE_NAME, data_asset_name=DATA_ASSET_NAME
)

# Create a new validator with an empty expectation suite
# If you have an expectation suite already created, create_expectation_suite=False
# overwrite_existing=False
logger.info("Validator init")
validator = init_validator(
    context,
    batch_request,
    EXPECTATION_SUITE_NAME,
    create_expectation_suite=True,
    overwrite_existing=True,
)

# create some new expectations
validator.expect_table_columns_to_match_ordered_list(["col_a", "col_b", "col_c"])
validator.expect_column_values_to_not_be_null("col_a")
validator.expect_column_values_to_not_be_null("col_b")
validator.expect_column_values_to_not_be_null("col_c")
validator.expect_column_values_to_be_unique("col_a")
validator.expect_column_values_to_be_unique("col_b")
validator.expect_column_values_to_be_unique("col_c")
validator.expect_table_row_count_to_equal(4)
validator.expect_column_values_to_be_of_type(column="col_a", type_="LongType")
validator.expect_column_values_to_be_of_type(column="col_b", type_="LongType")
validator.expect_column_values_to_be_of_type(column="col_c", type_="LongType")

# Check generated expectation suite
# only expectations with "success": true
validator.get_expectation_suite()
# all expectations
validator.get_expectation_suite(discard_failed_expectations=False)

validator.save_expectation_suite()

# Validate a fresh dataframe
df_new = pd.DataFrame(
    [[4, 2, 3], [4, 2, 1], [4, 2, 1], [10, 11, 1]], columns=["col_c", "col_a", "col_b"]
)

# Generate a batch of data
batch_request_new = get_batch_request(
    df_new, datasource_name=DATASOURCE_NAME, data_asset_name=DATA_ASSET_NAME
)

logger.info("Running Checkpoint")
checkpoint_result = run_checkpoint(
    context=context,
    checkpoint_name=CHECKPOINT_NAME,
    expectation_suite_name=EXPECTATION_SUITE_NAME,
    run_id=RUN_ID,
    batch_request=batch_request_new,
    action_list=config_dict["validation_operators"]["action_list_operator"][
        "action_list"
    ],
)

# take action based on results
if not checkpoint_result["success"]:
    raise Exception("Validation failed!")
logger.info("Validation succeeded!")

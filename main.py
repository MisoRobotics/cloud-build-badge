"""Push a badge in response to a build event"""
import base64
import json
import os
from string import Template

import google.cloud
from google.cloud import storage

from cloud_build_badge import BadgeMaker

_TRIGGER_TEMPLATE = "builds/${repo}/branches/${branch}/${trigger}.svg"
_RESEARCH_TEMPLATE = (
    "builds/research-builds/${test_name}/${flippy_tag}/${commitish}.svg"
)

_TRIGGER_REQUIRED_SUBS = ["REPO_NAME", "BRANCH_NAME", "TRIGGER_NAME"]
_RESEARCH_REQUIRED_SUBS = [
    "_TEST_NAME",
    "_FLIPPY_TAG_CLEAN",
    "_COMMITISH_CLEAN",
]


def copy_badge(bucket, obj, new_obj):
    """Copy a badge to a public cloud storage bucket."""
    client = storage.Client()

    try:
        bucket = client.get_bucket(bucket)
    except google.cloud.exceptions.NotFound as ex:
        raise RuntimeError(f"Could not find bucket {bucket}") from ex

    blob = bucket.get_blob(obj)
    if blob is None:
        raise RuntimeError(f"Couldn't find object {obj} in bucket {bucket}")

    bucket.copy_blob(blob, bucket, new_name=new_obj)


def build_badge(event, context) -> None:
    """Create an push a badge in response to a build event."""
    bucket = os.environ["BADGES_BUCKET"]

    decoded = base64.b64decode(event["data"]).decode("utf-8")
    data = json.loads(decoded)

    subs = data["substitutions"]
    tags = data["tags"]
    status = data["status"]

    # Create badge based on trigger
    if all(sub in subs for sub in _TRIGGER_REQUIRED_SUBS):
        repo = subs["REPO_NAME"]
        branch = subs["BRANCH_NAME"]
        trigger = subs["TRIGGER_NAME"]

        try:
            src = BadgeMaker.make_badge(trigger, status)
        except KeyError:
            src = f"badges/{status.lower()}.svg"
        dest = Template(_TRIGGER_TEMPLATE).substitute(
            repo=repo, branch=branch, trigger=trigger
        )
        copy_badge(bucket, src, dest)
        print(f"Created badge from trigger info: {dest}")

    # Create badge for research builds based on substitutions
    if "research" in tags and all(
        sub in subs for sub in _RESEARCH_REQUIRED_SUBS
    ):
        test_name = subs["_TEST_NAME"]
        flippy_tag = subs["_FLIPPY_TAG_CLEAN"]
        commitish = subs["_COMMITISH_CLEAN"]

        src = f"badges/{status.lower()}.svg"
        dest = Template(_RESEARCH_TEMPLATE).substitute(
            test_name=test_name, flippy_tag=flippy_tag, commitish=commitish
        )
        copy_badge(bucket, src, dest)
        print(f"Created badge from research build substitutions: {dest}")

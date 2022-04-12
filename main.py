"""Push a badge in response to a build event"""
import base64
import json
import os
from string import Template

import google.cloud
from google.cloud import storage

from cloud_build_badge import BadgeMaker

_DFEAULT_TEMPLATE = "builds/${repo}/branches/${branch}/${trigger}.svg"


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
    decoded = base64.b64decode(event["data"]).decode("utf-8")
    data = json.loads(decoded)

    subs = data["substitutions"]
    status = data["status"]
    bucket = os.environ["BADGES_BUCKET"]
    repo = subs["REPO_NAME"]
    branch = subs["BRANCH_NAME"]
    trigger = subs["TRIGGER_NAME"]

    tmpl = os.environ.get("TEMPLATE_PATH", _DFEAULT_TEMPLATE)
    try:
        src = BadgeMaker.make_badge(trigger, status)
    except KeyError:
        src = f"badges/{status.lower()}.svg"
    dest = Template(tmpl).substitute(repo=repo, branch=branch, trigger=trigger)
    copy_badge(bucket, src, dest)

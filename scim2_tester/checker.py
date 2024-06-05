import argparse
import uuid
from typing import List
from typing import Tuple

from httpx import HTTPError
from scim2_client import SCIMClient
from scim2_client import SCIMClientError
from scim2_models import Error
from scim2_models import Group
from scim2_models import Resource
from scim2_models import User

from scim2_tester.resource import check_resource_type
from scim2_tester.resource_types import check_resource_types_endpoint
from scim2_tester.schemas import check_schemas_endpoint
from scim2_tester.service_provider_config import check_service_provider_config_endpoint
from scim2_tester.utils import CheckResult
from scim2_tester.utils import Status
from scim2_tester.utils import decorate_result


@decorate_result
def check_random_url(scim: SCIMClient) -> Tuple[Resource, CheckResult]:
    """A request to a random URL should return a 404 Error object."""

    probably_invalid_url = f"/{str(uuid.uuid4())}"
    try:
        response = scim.query(url=probably_invalid_url)
    except HTTPError as exc:
        return CheckResult(
            status=Status.ERROR,
            reason=str(exc),
        )

    except SCIMClientError as exc:
        return CheckResult(
            status=Status.ERROR,
            reason=f"{probably_invalid_url} did not return an Error object",
            data=exc.response.content,
        )

    if not isinstance(response, Error):
        return CheckResult(
            status=Status.ERROR,
            reason=f"{probably_invalid_url} did not return an Error object",
            data=response,
        )

    if response.status != 404:
        return CheckResult(
            status=Status.ERROR,
            reason=f"{probably_invalid_url} did return an object, but the status code is {response.status}",
            data=response,
        )

    return CheckResult(
        status=Status.SUCCESS,
        reason=f"{probably_invalid_url} correctly returned a 404 error",
    ), response


def check_server(scim: SCIMClient) -> List[CheckResult]:
    """Perform a series of check to a SCIM server."""

    results = []

    # Get the initial basic objects
    result, service_provider_config = check_service_provider_config_endpoint(scim)
    results.append(result)
    result, schemas = check_schemas_endpoint(scim)
    results.append(result)
    result, resource_types = check_resource_types_endpoint(scim)
    results.append(result)

    # Miscelleaneous checks
    result = check_random_url(scim)
    results.append(result)

    # Resource checks
    for resource_type in resource_types:
        results.extend(
            check_resource_type(scim, resource_type, service_provider_config)
        )

    return results


if __name__ == "__main__":
    from httpx import Client

    parser = argparse.ArgumentParser(description="Process some integers.")
    parser.add_argument("host")
    parser.add_argument("--token", required=False)
    parser.add_argument("--verbose", required=False, action="store_true")
    args = parser.parse_args()

    client = Client(
        base_url=args.host,
        headers={"Authorization": f"Bearer {args.token}"} if args.token else None,
    )
    scim = SCIMClient(
        client,
        resource_types=(
            User,
            Group,
        ),
    )
    results = check_server(scim)
    for result in results:
        print(result.status.name, result.title)
        if result.reason:
            print("  ", result.reason)
            if args.verbose and result.data:
                print("  ", result.data)

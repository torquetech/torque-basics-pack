# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""TODO"""

import functools
import os
import subprocess

from collections import namedtuple

from torque import hlb
from torque import postgres
from torque import v1


Service = namedtuple("Service", [
    "proto",
    "host",
    "port"
])


class V1TaskImplementationInterface(v1.bond.Interface):
    """TODO"""

    def add_environment(self, name: str, value: v1.utils.Future[str] | str):
        """TODO"""

    def set_image(self, tag: str, id: str):
        """TODO"""

    def set_command(self, command: [str]):
        """TODO"""

    def set_arguments(self, arguments: [str]):
        """TODO"""

    def set_working_directory(self, working_directory: str):
        """TODO"""


class V1ServiceImplementationInterface(v1.bond.Interface):
    """TODO"""

    def add_environment(self, name: str, value: v1.utils.Future[str] | str):
        """TODO"""

    def set_image(self, tag: str, id: str):
        """TODO"""

    def set_command(self, command: [str]):
        """TODO"""

    def set_arguments(self, arguments: [str]):
        """TODO"""

    def set_working_directory(self, working_directory: str):
        """TODO"""

    def set_proto(self, proto: str):
        """TODO"""

    def set_port(self, port: int):
        """TODO"""

    def service(self) -> v1.utils.Future[Service] | Service:
        """TODO"""


class V1TCPSourceInterface(v1.component.SourceInterface):
    """TODO"""

    def service(self) -> v1.utils.Future[Service] | Service:
        """TODO"""


class V1HttpSourceInterface(v1.component.SourceInterface):
    """TODO"""

    def service(self) -> v1.utils.Future[Service] | Service:
        """TODO"""


class V1EnvironmentInterface(v1.component.DestinationInterface):
    """TODO"""

    def add(self, name: str, value: object):
        """TODO"""


class BaseComponent(v1.component.Component):
    """TODO"""

    PARAMETERS = {
        "defaults": {
            "build": {
                "command": [
                    "docker", "build",
                    "-t", "$IMAGE", "."
                ]
            },
            "run": {}
        },
        "schema": {
            "path": str,
            "build": {
                "command": [str]
            },
            "run": {
                v1.schema.Optional("command"): [str],
                v1.schema.Optional("arguments"): [str],
                v1.schema.Optional("work_directory"): str
            }
        }
    }

    def _resolve_cmd(self) -> [str]:
        """TODO"""

        cmd = []

        for i in self.parameters["build"]["command"]:
            i = i.replace("$IMAGE", f"{self.name}:latest")
            cmd.append(i)

        return cmd

    def _build(self) -> str:
        """TODO"""

        path = v1.utils.resolve_path(self.parameters["path"])
        cmd = self._resolve_cmd()

        print(f"+ {' '.join(cmd)}")
        subprocess.run(cmd,
                       env=os.environ,
                       cwd=path,
                       check=True)

        return f"{self.name}:latest"

    def _id(self) -> str:
        """TODO"""

        cmd = [
            "docker", "image", "inspect",
            "-f", "{{.Id}}",
            f"{self.name}:latest"
        ]

        print(f"+ {' '.join(cmd)}")

        p = subprocess.run(cmd,
                           env=os.environ,
                           check=True,
                           capture_output=True)

        return p.stdout.decode("utf8").strip()

    def on_interfaces(self):
        """TODO"""

        return [
            V1EnvironmentInterface(add=self.interfaces.impl.add_environment)
        ]

    def on_build(self):
        """TODO"""

        image = {
            "tag": self._build(),
            "id": self._id()
        }

        with self.context as ctx:
            ctx.set_data("images", self.name, image)

    def on_apply(self):
        """TODO"""

        with self.context as ctx:
            image = ctx.get_data("images", self.name)

        if not image:
            raise v1.exceptions.RuntimeError(f"{self.name}: image not found")

        self.interfaces.impl.set_image(image["tag"], image["id"])
        self.interfaces.impl.set_command(self.parameters["run"].get("command"))
        self.interfaces.impl.set_arguments(self.parameters["run"].get("arguments"))
        self.interfaces.impl.set_working_directory(self.parameters["run"].get("working_directory"))


class V1Task(BaseComponent):
    """TODO"""

    @classmethod
    def on_requirements(cls) -> dict[str, object]:
        """TODO"""

        return {
            "impl": {
                "interface": V1TaskImplementationInterface,
                "required": True
            }
        }


class BaseService(BaseComponent):
    """TODO"""

    PARAMETERS = v1.utils.merge_dicts(BaseComponent.PARAMETERS, {
        "defaults": {},
        "schema": {
            "port": str
        }
    })

    @classmethod
    def on_requirements(cls) -> dict[str, object]:
        """TODO"""

        return {
            "impl": {
                "interface": V1ServiceImplementationInterface,
                "required": True
            }
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._proto = None

    def on_apply(self):
        """TODO"""

        super().on_apply()

        self.interfaces.impl.set_proto(self._proto)
        self.interfaces.impl.set_port(int(self.parameters["port"]))


class V1TCPService(BaseService):
    """TODO"""

    PARAMETERS = v1.utils.merge_dicts(BaseService.PARAMETERS, {
        "defaults": {
            "proto": "tcp"
        },
        "schema": {
            "proto": str
        }
    })

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._proto = self.parameters["proto"]

    def on_interfaces(self):
        """TODO"""

        return super().on_interfaces() + [
            V1TCPSourceInterface(service=self.interfaces.impl.service)
        ]


class V1HttpService(BaseService):
    """TODO"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._proto = "http"

    def on_interfaces(self):
        """TODO"""

        return super().on_interfaces() + [
            V1HttpSourceInterface(service=self.interfaces.impl.service)
        ]


class V1IngressLink(v1.link.Link):
    """TODO"""

    PARAMETERS = {
        "defaults": {},
        "schema": {
            "host": str,
            "path": str
        }
    }

    @classmethod
    def on_requirements(cls):
        """TODO"""

        return {
            "src": {
                "interface": V1HttpSourceInterface,
                "required": True
            },
            "dst": {
                "interface": hlb.V1DestinationInterface,
                "required": True
            }
        }

    def on_apply(self):
        """TODO"""

        service = self.interfaces.src.service()

        if isinstance(service, v1.utils.Future):
            raise v1.exceptions.RuntimeError(f"{self.source}: cannot link remote object")

        self.interfaces.dst.add(hlb.Ingress(self.name,
                                            service.host,
                                            service.port,
                                            self.parameters["host"],
                                            self.parameters["path"],
                                            {}))


class BaseLink(v1.link.Link):
    """TODO"""

    @classmethod
    def on_requirements(cls):
        """TODO"""

        return {
            "dst": {
                "interface": V1EnvironmentInterface,
                "required": True
            }
        }

    def _resolve_uri(self, service: v1.utils.Future[Service] | Service):
        """TODO"""

        service = v1.utils.resolve_futures(service)

        return f"{service.proto}://{service.host}:{service.port}"

    def on_apply(self):
        """TODO"""

        service = self.interfaces.src.service()

        self.interfaces.dst.add(self.source.replace("-", "_"),
                                v1.utils.Future(functools.partial(self._resolve_uri,
                                                                  service)))


class V1PostgresLink(BaseLink):
    """TODO"""

    PARAMETERS = v1.utils.merge_dicts(BaseLink.PARAMETERS, {
        "defaults": {},
        "schema": {
            "database": str,
            "user": str
        }
    })

    @classmethod
    def on_requirements(cls):
        """TODO"""

        return super().on_requirements() | {
            "src": {
                "interface": postgres.V1SourceInterface,
                "required": True
            }
        }

    def _resolve_pg_uri(self,
                        auth: v1.utils.Future[postgres.Authorization],
                        service: v1.utils.Future[postgres.Service] | postgres.Service) -> str:
        """TODO"""

        auth = v1.utils.resolve_futures(auth)
        service = v1.utils.resolve_futures(service)

        args = "&".join([f"{k}={v}" for k, v in service.options.items()])

        return f"postgres://{auth.user}:{auth.password}@{service.host}:{service.port}/{auth.database}?{args}"

    def on_apply(self):
        """TODO"""

        auth = self.interfaces.src.auth(self.parameters["database"],
                                        self.parameters["user"])

        service = self.interfaces.src.service()

        self.interfaces.dst.add(self.source.replace("-", "_"),
                                v1.utils.Future(functools.partial(self._resolve_pg_uri,
                                                                  auth,
                                                                  service)))


class V1TCPServiceLink(BaseLink):
    """TODO"""

    @classmethod
    def on_requirements(cls):
        """TODO"""

        return super().on_requirements() | {
            "src": {
                "interface": V1TCPSourceInterface,
                "required": True
            }
        }


class V1HttpServiceLink(BaseLink):
    """TODO"""

    @classmethod
    def on_requirements(cls):
        """TODO"""

        return super().on_requirements() | {
            "src": {
                "interface": V1HttpSourceInterface,
                "required": True
            }
        }


repository = {
    "v1": {
        "components": [
            V1Task,
            V1TCPService,
            V1HttpService
        ],
        "links": [
            V1IngressLink,
            V1PostgresLink,
            V1TCPServiceLink,
            V1HttpServiceLink
        ]
    }
}

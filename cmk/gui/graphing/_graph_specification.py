#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from typing import Annotated, Callable, Literal

from pydantic import BaseModel, Field, parse_obj_as
from typing_extensions import TypedDict

from livestatus import SiteId

from cmk.utils.hostaddress import HostName
from cmk.utils.metrics import MetricName
from cmk.utils.servicename import ServiceName

from cmk.gui.type_defs import SingleInfos, TranslatedMetric, VisualContext

from ._type_defs import GraphConsoldiationFunction, GraphPresentation, LineType, Operators

HorizontalRule = tuple[float, str, str, str]


@dataclass(frozen=True, kw_only=True)
class MetricDefinition:
    expression: str
    line_type: LineType
    title: str = ""


@dataclass(frozen=True)
class CombinedSingleMetricSpec:
    datasource: str
    context: VisualContext
    selected_metric: MetricDefinition
    consolidation_function: GraphConsoldiationFunction
    presentation: GraphPresentation


@dataclass(frozen=True)
class NeededElementForTranslation:
    host_name: HostName
    service_name: ServiceName


@dataclass(frozen=True)
class NeededElementForRRDDataKey:
    # TODO Intermediate step, will be cleaned up:
    # Relates to MetricOperation::rrd with SiteId, etc.
    site_id: SiteId
    host_name: HostName
    service_name: ServiceName
    metric_name: str
    consolidation_func_name: GraphConsoldiationFunction | None
    scale: float


RetranslationMap = Mapping[
    tuple[HostName, ServiceName], Mapping[MetricName, tuple[SiteId, TranslatedMetric]]
]


class MetricOpConstant(BaseModel, frozen=True):
    ident: Literal["constant"] = "constant"
    value: float

    def needed_elements(
        self,
        resolve_combined_single_metric_spec: Callable[
            [CombinedSingleMetricSpec], Sequence[GraphMetric]
        ],
    ) -> Iterator[NeededElementForTranslation | NeededElementForRRDDataKey]:
        yield from ()

    def reverse_translate(self, retranslation_map: RetranslationMap) -> MetricOperation:
        return self


class MetricOpScalar(BaseModel, frozen=True):
    ident: Literal["scalar"] = "scalar"
    host_name: HostName
    service_name: ServiceName
    metric_name: MetricName
    scalar_name: Literal["warn", "crit", "min", "max"] | None

    def needed_elements(
        self,
        resolve_combined_single_metric_spec: Callable[
            [CombinedSingleMetricSpec], Sequence[GraphMetric]
        ],
    ) -> Iterator[NeededElementForTranslation | NeededElementForRRDDataKey]:
        yield NeededElementForTranslation(self.host_name, self.service_name)

    def reverse_translate(self, retranslation_map: RetranslationMap) -> MetricOperation:
        _site, trans = retranslation_map[(self.host_name, self.service_name)][self.metric_name]
        if not isinstance(value := trans["scalar"].get(str(self.scalar_name)), float):
            # TODO if scalar_name not in trans["scalar"] -> crash; No warning to the user :(
            raise TypeError(value)
        return MetricOpConstant(value=value)


class MetricOpOperator(BaseModel, frozen=True):
    ident: Literal["operator"] = "operator"
    operator_name: Operators
    operands: Sequence[MetricOperation] = []

    def needed_elements(
        self,
        resolve_combined_single_metric_spec: Callable[
            [CombinedSingleMetricSpec], Sequence[GraphMetric]
        ],
    ) -> Iterator[NeededElementForTranslation | NeededElementForRRDDataKey]:
        yield from (
            ne
            for o in self.operands
            for ne in o.needed_elements(resolve_combined_single_metric_spec)
        )

    def reverse_translate(self, retranslation_map: RetranslationMap) -> MetricOperation:
        return MetricOpOperator(
            operator_name=self.operator_name,
            operands=[o.reverse_translate(retranslation_map) for o in self.operands],
        )


class TransformationParametersPercentile(BaseModel, frozen=True):
    percentile: int


class TransformationParametersForecast(BaseModel, frozen=True):
    past: (
        Literal["m1", "m3", "m6", "y0", "y1"]
        | tuple[Literal["age"], int]
        | tuple[Literal["date"], tuple[float, float]]
    )
    future: (
        Literal["m-1", "m-3", "m-6", "y-1"]
        | tuple[Literal["next"], int]
        | tuple[Literal["until"], float]
    )
    changepoint_prior_scale: Literal["0.001", "0.01", "0.05", "0.1", "0.2"]
    seasonality_mode: Literal["additive", "multiplicative"]
    interval_width: Literal["0.68", "0.86", "0.95"]
    display_past: int
    display_model_parametrization: bool


# TODO transformation is not part of cre but we first have to fix all types
class MetricOpTransformation(BaseModel, frozen=True):
    ident: Literal["transformation"] = "transformation"
    parameters: TransformationParametersPercentile | TransformationParametersForecast
    operands: Sequence[MetricOperation]

    def needed_elements(
        self,
        resolve_combined_single_metric_spec: Callable[
            [CombinedSingleMetricSpec], Sequence[GraphMetric]
        ],
    ) -> Iterator[NeededElementForTranslation | NeededElementForRRDDataKey]:
        yield from (
            ne
            for o in self.operands
            for ne in o.needed_elements(resolve_combined_single_metric_spec)
        )

    def reverse_translate(self, retranslation_map: RetranslationMap) -> MetricOperation:
        return MetricOpTransformation(
            parameters=self.parameters,
            operands=[o.reverse_translate(retranslation_map) for o in self.operands],
        )


# TODO Check: Similar to CombinedSingleMetricSpec
class SingleMetricSpec(TypedDict):
    datasource: str
    context: VisualContext
    selected_metric: MetricDefinition
    consolidation_function: GraphConsoldiationFunction | None
    presentation: GraphPresentation
    single_infos: list[str]


# TODO combined is not part of cre but we first have to fix all types
class MetricOpCombined(BaseModel, frozen=True):
    ident: Literal["combined"] = "combined"
    single_metric_spec: SingleMetricSpec

    def needed_elements(
        self,
        resolve_combined_single_metric_spec: Callable[
            [CombinedSingleMetricSpec], Sequence[GraphMetric]
        ],
    ) -> Iterator[NeededElementForTranslation | NeededElementForRRDDataKey]:
        if (consolidation_func_name := self.single_metric_spec["consolidation_function"]) is None:
            raise TypeError(consolidation_func_name)

        for metric in resolve_combined_single_metric_spec(
            CombinedSingleMetricSpec(
                datasource=self.single_metric_spec["datasource"],
                context=self.single_metric_spec["context"],
                selected_metric=self.single_metric_spec["selected_metric"],
                consolidation_function=consolidation_func_name,
                presentation=self.single_metric_spec["presentation"],
            )
        ):
            yield from metric.operation.needed_elements(resolve_combined_single_metric_spec)

    def reverse_translate(self, retranslation_map: RetranslationMap) -> MetricOperation:
        return self


class MetricOpRRDSource(BaseModel, frozen=True):
    ident: Literal["rrd"] = "rrd"
    site_id: SiteId
    host_name: HostName
    service_name: ServiceName
    metric_name: MetricName
    consolidation_func_name: GraphConsoldiationFunction | None
    scale: float

    def needed_elements(
        self,
        resolve_combined_single_metric_spec: Callable[
            [CombinedSingleMetricSpec], Sequence[GraphMetric]
        ],
    ) -> Iterator[NeededElementForTranslation | NeededElementForRRDDataKey]:
        yield NeededElementForRRDDataKey(
            self.site_id,
            self.host_name,
            self.service_name,
            self.metric_name,
            self.consolidation_func_name,
            self.scale,
        )

    def reverse_translate(self, retranslation_map: RetranslationMap) -> MetricOperation:
        site_id, trans = retranslation_map[(self.host_name, self.service_name)][self.metric_name]
        metrics: list[MetricOperation] = [
            MetricOpRRDSource(
                site_id=site_id,
                host_name=self.host_name,
                service_name=self.service_name,
                metric_name=name,
                consolidation_func_name=self.consolidation_func_name,
                scale=scale,
            )
            for name, scale in zip(trans["orig_name"], trans["scale"])
        ]

        if len(metrics) > 1:
            return MetricOpOperator(operator_name="MERGE", operands=metrics)

        return metrics[0]


class MetricOpRRDChoice(BaseModel, frozen=True):
    ident: Literal["rrd_choice"] = "rrd_choice"
    host_name: HostName
    service_name: ServiceName
    metric_name: MetricName
    consolidation_func_name: GraphConsoldiationFunction | None

    def needed_elements(
        self,
        resolve_combined_single_metric_spec: Callable[
            [CombinedSingleMetricSpec], Sequence[GraphMetric]
        ],
    ) -> Iterator[NeededElementForTranslation | NeededElementForRRDDataKey]:
        yield NeededElementForTranslation(self.host_name, self.service_name)

    def reverse_translate(self, retranslation_map: RetranslationMap) -> MetricOperation:
        site_id, trans = retranslation_map[(self.host_name, self.service_name)][self.metric_name]
        metrics: list[MetricOperation] = [
            MetricOpRRDSource(
                site_id=site_id,
                host_name=self.host_name,
                service_name=self.service_name,
                metric_name=name,
                consolidation_func_name=self.consolidation_func_name,
                scale=scale,
            )
            for name, scale in zip(trans["orig_name"], trans["scale"])
        ]

        if len(metrics) > 1:
            return MetricOpOperator(operator_name="MERGE", operands=metrics)

        return metrics[0]


MetricOperation = (
    MetricOpConstant
    | MetricOpOperator
    | MetricOpTransformation
    | MetricOpCombined
    | MetricOpRRDSource
    | MetricOpRRDChoice
    | MetricOpScalar
)


MetricOpOperator.model_rebuild()
MetricOpTransformation.model_rebuild()


class GraphMetric(BaseModel, frozen=True):
    title: str
    line_type: LineType
    operation: MetricOperation
    unit: str
    color: str
    visible: bool


class TemplateGraphSpecification(BaseModel, frozen=True):
    graph_type: Literal["template"] = "template"
    site: SiteId | None
    host_name: HostName
    service_description: ServiceName
    graph_index: int | None = None
    graph_id: str | None = None
    destination: str | None = None


class CombinedGraphSpecification(BaseModel, frozen=True):
    graph_type: Literal["combined"] = "combined"
    datasource: str
    single_infos: SingleInfos
    presentation: GraphPresentation
    context: VisualContext
    graph_template: str
    selected_metric: MetricDefinition | None = None
    consolidation_function: GraphConsoldiationFunction | None = None
    destination: str | None = None


class CustomGraphSpecification(BaseModel, frozen=True):
    graph_type: Literal["custom"] = "custom"
    id: str


class ExplicitGraphSpecification(BaseModel, frozen=True):
    graph_type: Literal["explicit"] = "explicit"
    title: str
    unit: str
    consolidation_function: GraphConsoldiationFunction | None
    explicit_vertical_range: tuple[float | None, float | None]
    omit_zero_metrics: bool
    horizontal_rules: Sequence[HorizontalRule]
    metrics: Sequence[GraphMetric]
    mark_requested_end_time: bool = False


class SingleTimeseriesGraphSpecification(BaseModel, frozen=True):
    graph_type: Literal["single_timeseries"] = "single_timeseries"
    site: SiteId
    metric: MetricName
    host: HostName | None = None
    service: ServiceName | None = None
    service_description: ServiceName | None = None
    color: str | None = None


class ForecastGraphSpecification(BaseModel, frozen=True):
    graph_type: Literal["forecast"] = "forecast"
    id: str
    destination: str | None = None


GraphSpecification = Annotated[
    (
        TemplateGraphSpecification
        | CombinedGraphSpecification
        | CustomGraphSpecification
        | ExplicitGraphSpecification
        | SingleTimeseriesGraphSpecification
        | ForecastGraphSpecification
    ),
    Field(discriminator="graph_type"),
]


def parse_raw_graph_specification(raw: Mapping[str, object]) -> GraphSpecification:
    # See https://github.com/pydantic/pydantic/issues/1847 and the linked mypy issue for the
    # suppressions below
    return parse_obj_as(GraphSpecification, raw)  # type: ignore[arg-type]

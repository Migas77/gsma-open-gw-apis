{{/*
Expand the name of the chart.
*/}}
{{- define "gsma-open-gateway.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "gsma-open-gateway.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "gsma-open-gateway.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "gsma-open-gateway.labels" -}}
helm.sh/chart: {{ include "gsma-open-gateway.chart" . }}
{{ include "gsma-open-gateway.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "gsma-open-gateway.selectorLabels" -}}
app.kubernetes.io/name: {{ include "gsma-open-gateway.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "gsma-open-gateway.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "gsma-open-gateway.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Whether the gateway needs CAPIF connection settings (host, ports, credentials):
true for the provider side (capif.enabled) and for the invoker side, where the
gateway reaches NEF through the same CAPIF core (nef.auth_mode == "capif").
Only the provider side needs the onboarding-cert volume, which stays gated on
.Values.capif.enabled directly.
*/}}
{{- define "gsma-open-gateway.capifRequired" -}}
{{- if or .Values.capif.enabled (eq (dig "nef" "auth_mode" "" (.Values.gatewayConfig | default dict)) "capif") -}}
true
{{- end -}}
{{- end }}

{{/*
Secret holding the NEF basic-auth credentials: the chart-created one, or a
pre-existing Secret in this namespace. Empty when neither is configured.
*/}}
{{- define "gsma-open-gateway.nefSecretName" -}}
{{- if .Values.nefSecret.create -}}
{{- printf "%s-nef" (include "gsma-open-gateway.fullname" .) -}}
{{- else -}}
{{- .Values.nefSecret.name -}}
{{- end -}}
{{- end }}

{{- define "fov-quicklook.env.s3_tile" -}}
- name: QUICKLOOK_s3_tile
  value: {{ .Values.s3_tile | toJson | quote }}
- name: QUICKLOOK_s3_tile__access_key
  valueFrom:
    secretKeyRef:
      name: fov-quicklook
      key: s3_repository_access_key
- name: QUICKLOOK_s3_tile__secret_key
  valueFrom:
    secretKeyRef:
      name: fov-quicklook
      key: s3_repository_secret_key
{{- end }}

{{- define "fov-quicklook.env.s3_test_data" -}}
{{ if .Values.s3_test_data }}
- name: QUICKLOOK_s3_test_data
  value: {{ .Values.s3_test_data | toJson | quote }}
- name: QUICKLOOK_s3_test_data__access_key
  value: quicklook
- name: QUICKLOOK_s3_test_data__secret_key
  value: password
{{ end }}
{{- end }}

{{- define "quicklook.ingress.spec" -}}
rules:
  - http:
      paths:
        - path: {{ .Values.config.pathPrefix }}
          pathType: Prefix
          backend:
            service:
              name: fov-quicklook-frontend
              port:
                number: 9500
{{- end -}}

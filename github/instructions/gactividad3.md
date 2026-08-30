
Se va a trabajar en una actividad de la asignatura observabilidad en ambientes productivos basados en la informacion que tenemos hasta el momento en D:\Maestria\Semestre II\Observabilidad\Actividad 3\otel-microservices se deben responder todos los puntos que se tiene en la sección "Descripcion de la activdad" si hay cosas que no se pueden subir a la nube se puede hacer local en docker o como sea mas conveniente. tener en cuenta los entregables y los criterios de evaluación este será un trabajo en conjunto entre Leonardo Pérez Ramírez, Ivan Felipe Vera Triana y Juan Felipe Gonzalez Ortiz.


## LAB integrador: Sistema de observabilidad end-to-end con AIOps y resiliencia en GCP y AWS


## Introducción al momento
Integrar todos los dominios del Observability (Tres Pilares, OpenTelemetry, AIOps, Network Observability, DataOps, SRE) en un sistema observable completo desplegado en producción simulada sobre GCP y AWS, demostrando detección automática de anomalías, respuesta a incidentes basada en datos y validación de resiliencia mediante experimentos de caos controlados.


## Indicador de desempeño
Utilizar herramientas de observabilidad favoreciendo la detección y resolución de problemas en tiempo real, mejorando la resiliencia del sistema.


## Descripción de la actividad
Este laboratorio integrador extiende y enriquece los laboratorios anteriores (2.2) hacia un sistema observable de nivel producción.

Módulo A — Arquitectura Observable Completa:
Extender la arquitectura con un tercer microservicio (data-service) que acceda a GCP Cloud SQL y AWS RDS.
Instrumentar completamente con OTel SDK (3 pilares) incluyendo database spans con OTel DB Semantic Conventions.
Implementar service mesh básico (Cloud Service Mesh / AWS App Mesh) para observabilidad de red L7.

Módulo B — AIOps: Detección Automática de Anomalías:
Configurar GCP Cloud Monitoring Anomaly Detection o AWS DevOps Guru en el servicio data-service.
Implementar una regla de correlación: cuando error_rate > baseline + 2σ Y latency_p99 > SLO_threshold → alerta enriquecida con trace_id del request fallido.
Demostrar reducción de alertas ruidosas vs. sistema con umbrales estáticos.

Módulo C — Network and Security Observability:
Habilitar VPC Flow Logs (GCP) y VPC Flow Logs (AWS). Configurar alertas sobre tráfico anómalo entre servicios.
Implementar Security Command Center (GCP) o AWS Security Hub básico para observabilidad de seguridad.
Crear dashboard de 'Golden Signals de Seguridad': intentos de autenticación fallidos, tráfico N-S/E-W, CVEs activos.

Módulo D — Chaos Engineering Controlado:
Ejecutar 2 experimentos de caos: (1) inyección de latencia en service-b (200ms), (2) error rate 10% en data-service.
Verificar que el sistema de observabilidad detecta y alerta en < 2 minutos (MTTD objetivo).
Documentar: ¿Se degradó el SLO? ¿El error budget se consumió? ¿La alerta fue accionable?

Módulo E — Reporte de Madurez de Observabilidad:
Autoevaluar la solución contra el Observability Foundation Blueprint (8 dominios) con escala de madurez 1–5.
Proponer el roadmap de mejora para alcanzar el siguiente nivel de madurez en 3 meses.



## Entregables:

Repositorio GitHub con:
Toda la IaC
Código de instrumentación
Configuraciones y scripts
Video de demostración:
Video de demostración en vivo

Reporte ejecutivo final:
PDF de 10 páginas con arquitectura completa, evidencias de todos los pilares y análisis de madurez de observabilidad


## Criterios de calificación

Arquitectura Observable Completa: 
Tres microservicios instrumentados con OTel, service mesh y correlación completa en ambas clouds.
1.25 puntos

AIOps: Detección de Anomalías y Correlación:
Detección automática funcional con correlación y evidencia cuantitativa.
1 puntos

Network & Security Observability:
Observabilidad de red y seguridad funcional en ambas clouds con dashboards y alertas.
1 puntos


Chaos Engineering y Validación de MTTD:
Dos experimentos de caos ejecutados, MTTD ≤ 2 minutos y análisis de SLO/error budget.
1 puntos


Reporte de Madurez y Presentación Técnica:
Autoevaluación completa, roadmap accionable y demostración técnica en vivo.
0.75 puntos
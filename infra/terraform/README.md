# Aegis-Air Terraform

Minimal Cloud Run deployment skeleton for the `Aegis-Air` engine.

## Apply

```bash
terraform init
terraform apply \
  -var="project_id=your-project" \
  -var="image=asia-northeast3-docker.pkg.dev/your-project/apps/aegis-air:latest"
```

Use `env` to inject `AEGIS_AIR_OPERATOR_TOKEN`, target metadata URLs, and runtime tuning values.

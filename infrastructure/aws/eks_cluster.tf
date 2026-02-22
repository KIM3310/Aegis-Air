module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 20.0"

  cluster_name    = "aegis-air-cluster"
  cluster_version = "1.29"

  cluster_endpoint_public_access  = false # Force VPN or Direct Connect access for Zero-Trust
  cluster_endpoint_private_access = true

  vpc_id                   = module.vpc.vpc_id
  subnet_ids               = module.vpc.private_subnets
  control_plane_subnet_ids = module.vpc.private_subnets

  # EKS Managed Node Group(s)
  eks_managed_node_groups = {
    # Node group for the vulnerable E-commerce application
    target_apps = {
      min_size     = 1
      max_size     = 3
      desired_size = 2
      instance_types = ["t3.medium"]
    }
    # Node group handling local AI inferences (Requires more RAM/CPU)
    aegis_engine = {
      min_size     = 1
      max_size     = 2
      desired_size = 1
      instance_types = ["g4dn.xlarge"] # Using GPU instances for fast local LLM loading
      labels = {
        role = "zero-trust-llm"
      }
    }
  }

  tags = {
    Environment = "production"
    Project     = "Aegis-Air"
  }
}

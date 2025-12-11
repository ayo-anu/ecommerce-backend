# ==============================================================================
# Terraform Main Configuration
# Infrastructure as Code for E-Commerce Platform
# ==============================================================================

terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.24"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.12"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  # Remote State Backend
  backend "s3" {
    bucket         = "ecommerce-terraform-state"
    key            = "production/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-state-lock"
    kms_key_id     = "alias/terraform-state"
  }
}

# ==============================================================================
# Provider Configuration
# ==============================================================================

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Environment = var.environment
      Project     = "ecommerce-platform"
      ManagedBy   = "terraform"
      Owner       = "platform-team"
      CostCenter  = "engineering"
    }
  }
}

provider "kubernetes" {
  host                   = module.eks.cluster_endpoint
  cluster_ca_certificate = base64decode(module.eks.cluster_certificate_authority_data)

  exec {
    api_version = "client.authentication.k8s.io/v1beta1"
    command     = "aws"
    args = [
      "eks",
      "get-token",
      "--cluster-name",
      module.eks.cluster_name
    ]
  }
}

provider "helm" {
  kubernetes {
    host                   = module.eks.cluster_endpoint
    cluster_ca_certificate = base64decode(module.eks.cluster_certificate_authority_data)

    exec {
      api_version = "client.authentication.k8s.io/v1beta1"
      command     = "aws"
      args = [
        "eks",
        "get-token",
        "--cluster-name",
        module.eks.cluster_name
      ]
    }
  }
}

# ==============================================================================
# Data Sources
# ==============================================================================

data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_caller_identity" "current" {}

# ==============================================================================
# Local Variables
# ==============================================================================

locals {
  name   = "ecommerce-${var.environment}"
  region = var.aws_region

  vpc_cidr = "10.0.0.0/16"
  azs      = slice(data.aws_availability_zones.available.names, 0, 3)

  tags = {
    Environment = var.environment
    Project     = "ecommerce-platform"
  }
}

# ==============================================================================
# Networking Module
# ==============================================================================

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"

  name = local.name
  cidr = local.vpc_cidr

  azs             = local.azs
  private_subnets = [for k, v in local.azs : cidrsubnet(local.vpc_cidr, 4, k)]
  public_subnets  = [for k, v in local.azs : cidrsubnet(local.vpc_cidr, 8, k + 48)]
  database_subnets = [for k, v in local.azs : cidrsubnet(local.vpc_cidr, 8, k + 51)]

  enable_nat_gateway   = true
  single_nat_gateway   = var.environment == "development" ? true : false
  enable_dns_hostnames = true
  enable_dns_support   = true

  # VPC Flow Logs
  enable_flow_log                      = true
  create_flow_log_cloudwatch_iam_role  = true
  create_flow_log_cloudwatch_log_group = true

  # Kubernetes tags
  public_subnet_tags = {
    "kubernetes.io/role/elb" = "1"
    "kubernetes.io/cluster/${local.name}" = "shared"
  }

  private_subnet_tags = {
    "kubernetes.io/role/internal-elb" = "1"
    "kubernetes.io/cluster/${local.name}" = "shared"
  }

  tags = local.tags
}

# ==============================================================================
# EKS Cluster Module
# ==============================================================================

module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 19.0"

  cluster_name    = local.name
  cluster_version = "1.28"

  # Network Configuration
  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets

  # Control Plane Logging
  cluster_enabled_log_types = [
    "api",
    "audit",
    "authenticator",
    "controllerManager",
    "scheduler"
  ]

  # Cluster Endpoint Access
  cluster_endpoint_private_access = true
  cluster_endpoint_public_access  = true
  cluster_endpoint_public_access_cidrs = var.cluster_endpoint_public_access_cidrs

  # IRSA (IAM Roles for Service Accounts)
  enable_irsa = true

  # Encryption
  cluster_encryption_config = {
    resources        = ["secrets"]
    provider_key_arn = aws_kms_key.eks.arn
  }

  # Managed Node Groups
  eks_managed_node_groups = {
    # General Purpose Nodes
    general = {
      name           = "${local.name}-general"
      instance_types = ["t3.large"]

      min_size     = 3
      max_size     = 10
      desired_size = 3

      labels = {
        role = "general"
      }

      taints = []

      block_device_mappings = {
        xvda = {
          device_name = "/dev/xvda"
          ebs = {
            volume_size = 100
            volume_type = "gp3"
            iops        = 3000
            throughput  = 125
            encrypted   = true
            kms_key_id  = aws_kms_key.ebs.arn
          }
        }
      }
    }

    # AI/ML Workload Nodes (GPU optional)
    ai_workloads = {
      name           = "${local.name}-ai"
      instance_types = ["c5.2xlarge"]  # CPU-optimized for AI inference

      min_size     = 2
      max_size     = 20
      desired_size = 2

      labels = {
        role     = "ai-workloads"
        workload = "ml-inference"
      }

      taints = [{
        key    = "ai-workload"
        value  = "true"
        effect = "NoSchedule"
      }]

      block_device_mappings = {
        xvda = {
          device_name = "/dev/xvda"
          ebs = {
            volume_size = 200
            volume_type = "gp3"
            iops        = 3000
            encrypted   = true
            kms_key_id  = aws_kms_key.ebs.arn
          }
        }
      }
    }

    # Database Nodes (for stateful workloads)
    database = {
      name           = "${local.name}-database"
      instance_types = ["r5.xlarge"]  # Memory-optimized

      min_size     = 2
      max_size     = 4
      desired_size = 2

      labels = {
        role     = "database"
        workload = "stateful"
      }

      taints = [{
        key    = "database"
        value  = "true"
        effect = "NoSchedule"
      }]

      block_device_mappings = {
        xvda = {
          device_name = "/dev/xvda"
          ebs = {
            volume_size = 200
            volume_type = "gp3"
            iops        = 4000
            encrypted   = true
            kms_key_id  = aws_kms_key.ebs.arn
          }
        }
      }
    }
  }

  # Security Groups
  node_security_group_additional_rules = {
    ingress_allow_access_from_control_plane = {
      type                          = "ingress"
      protocol                      = "tcp"
      from_port                     = 9443
      to_port                       = 9443
      source_cluster_security_group = true
      description                   = "Allow access from control plane to webhook port of AWS load balancer controller"
    }
  }

  tags = local.tags
}

# ==============================================================================
# KMS Keys for Encryption
# ==============================================================================

resource "aws_kms_key" "eks" {
  description             = "EKS Secret Encryption Key"
  deletion_window_in_days = 7
  enable_key_rotation     = true

  tags = merge(local.tags, {
    Name = "${local.name}-eks-secrets"
  })
}

resource "aws_kms_alias" "eks" {
  name          = "alias/${local.name}-eks"
  target_key_id = aws_kms_key.eks.key_id
}

resource "aws_kms_key" "ebs" {
  description             = "EBS Volume Encryption Key"
  deletion_window_in_days = 7
  enable_key_rotation     = true

  tags = merge(local.tags, {
    Name = "${local.name}-ebs"
  })
}

resource "aws_kms_alias" "ebs" {
  name          = "alias/${local.name}-ebs"
  target_key_id = aws_kms_key.ebs.key_id
}

# ==============================================================================
# RDS Database
# ==============================================================================

module "rds" {
  source  = "terraform-aws-modules/rds/aws"
  version = "~> 6.0"

  identifier = "${local.name}-postgres"

  engine               = "postgres"
  engine_version       = "15.4"
  family               = "postgres15"
  major_engine_version = "15"
  instance_class       = var.rds_instance_class

  allocated_storage     = 100
  max_allocated_storage = 1000
  storage_encrypted     = true
  kms_key_id            = aws_kms_key.rds.arn

  db_name  = "ecommerce"
  username = "ecommerce_admin"
  port     = 5432

  multi_az               = var.environment == "production" ? true : false
  db_subnet_group_name   = module.vpc.database_subnet_group_name
  vpc_security_group_ids = [aws_security_group.rds.id]

  maintenance_window              = "Mon:00:00-Mon:03:00"
  backup_window                   = "03:00-06:00"
  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]

  backup_retention_period = var.environment == "production" ? 30 : 7
  skip_final_snapshot     = var.environment != "production"
  deletion_protection     = var.environment == "production"

  # Performance Insights
  performance_insights_enabled          = true
  performance_insights_retention_period = 7
  create_monitoring_role                = true
  monitoring_interval                   = 60

  tags = local.tags
}

resource "aws_kms_key" "rds" {
  description             = "RDS Encryption Key"
  deletion_window_in_days = 7
  enable_key_rotation     = true

  tags = merge(local.tags, {
    Name = "${local.name}-rds"
  })
}

# ==============================================================================
# ElastiCache Redis
# ==============================================================================

module "redis" {
  source  = "cloudposse/elasticache-redis/aws"
  version = "~> 0.52"

  name               = local.name
  vpc_id             = module.vpc.vpc_id
  subnets            = module.vpc.private_subnets
  security_group_ids = [aws_security_group.redis.id]

  cluster_mode_enabled    = true
  cluster_size            = 3
  instance_type           = var.redis_instance_type
  engine_version          = "7.0"
  family                  = "redis7"
  port                    = 6379
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  auth_token_enabled         = true

  parameter = [
    {
      name  = "maxmemory-policy"
      value = "allkeys-lru"
    }
  ]

  tags = local.tags
}

# ==============================================================================
# S3 Buckets
# ==============================================================================

module "s3_media" {
  source  = "terraform-aws-modules/s3-bucket/aws"
  version = "~> 3.0"

  bucket = "${local.name}-media"
  acl    = "private"

  versioning = {
    enabled = true
  }

  server_side_encryption_configuration = {
    rule = {
      apply_server_side_encryption_by_default = {
        sse_algorithm     = "aws:kms"
        kms_master_key_id = aws_kms_key.s3.arn
      }
    }
  }

  lifecycle_rule = [
    {
      id      = "delete-old-versions"
      enabled = true

      noncurrent_version_expiration = {
        days = 90
      }
    }
  ]

  tags = local.tags
}

resource "aws_kms_key" "s3" {
  description             = "S3 Encryption Key"
  deletion_window_in_days = 7
  enable_key_rotation     = true

  tags = merge(local.tags, {
    Name = "${local.name}-s3"
  })
}

# ==============================================================================
# Outputs
# ==============================================================================

output "cluster_endpoint" {
  description = "Endpoint for EKS control plane"
  value       = module.eks.cluster_endpoint
}

output "cluster_name" {
  description = "Kubernetes Cluster Name"
  value       = module.eks.cluster_name
}

output "rds_endpoint" {
  description = "RDS instance endpoint"
  value       = module.rds.db_instance_endpoint
  sensitive   = true
}

output "redis_endpoint" {
  description = "Redis cluster endpoint"
  value       = module.redis.endpoint
  sensitive   = true
}

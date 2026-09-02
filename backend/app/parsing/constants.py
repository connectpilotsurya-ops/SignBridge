SECTION_HEADINGS = {
    "experience": ["experience", "work experience", "employment history", "professional experience"],
    "education": ["education", "academic background"],
    "skills": ["skills", "technical skills", "core competencies", "technologies"],
    "projects": ["projects", "personal projects", "key projects"],
    "certifications": ["certifications", "certificates", "licenses"],
    "summary": ["summary", "profile", "objective", "about"],
    "achievements": ["achievements", "awards", "accomplishments"],
}

# Generic tech vocabulary used by the integrity detector to decide whether a
# suspicious region (hidden text, tiny font, footer) contains skill-shaped
# keywords worth calling out by name in a flag's evidence_text. This is
# intentionally broad/generic — the job-specific normalized_terms (from
# JobRequirement) are what actually zero out matching weight downstream.
TECH_VOCAB = [
    "python", "java", "javascript", "typescript", "react", "angular", "vue",
    "node", "node.js", "fastapi", "django", "flask", "spring", "docker",
    "kubernetes", "k8s", "aws", "azure", "gcp", "terraform", "ansible",
    "postgresql", "postgres", "mysql", "mongodb", "redis", "kafka",
    "graphql", "rest", "rest api", "grpc", "microservices", "ci/cd", "jenkins",
    "git", "linux", "c++", "c#", "go", "golang", "rust", "scala",
    "machine learning", "deep learning", "tensorflow", "pytorch",
    "devops", "sql", "nosql", "elasticsearch", "spark", "hadoop",
    "container orchestration", "docker swarm", "aws ecs", "ecs",
    "helm", "cloudformation", "pulumi", "vue.js",
]

# Nicer display casing for the requirement/claim UI — falls back to
# term.title() in code when a term isn't listed here.
DISPLAY_NAMES: dict[str, str] = {
    "python": "Python", "java": "Java", "javascript": "JavaScript",
    "typescript": "TypeScript", "react": "React", "angular": "Angular",
    "vue": "Vue", "vue.js": "Vue.js", "node": "Node.js", "node.js": "Node.js",
    "fastapi": "FastAPI", "django": "Django", "flask": "Flask",
    "spring": "Spring", "docker": "Docker", "kubernetes": "Kubernetes",
    "k8s": "Kubernetes", "aws": "AWS", "azure": "Azure", "gcp": "GCP",
    "terraform": "Terraform", "ansible": "Ansible", "postgresql": "PostgreSQL",
    "postgres": "PostgreSQL", "mysql": "MySQL", "mongodb": "MongoDB",
    "redis": "Redis", "kafka": "Kafka", "graphql": "GraphQL", "rest": "REST",
    "rest api": "REST API", "grpc": "gRPC", "microservices": "Microservices",
    "ci/cd": "CI/CD", "jenkins": "Jenkins", "git": "Git", "linux": "Linux",
    "c++": "C++", "c#": "C#", "go": "Go", "golang": "Go", "rust": "Rust",
    "scala": "Scala", "machine learning": "Machine Learning",
    "deep learning": "Deep Learning", "tensorflow": "TensorFlow",
    "pytorch": "PyTorch", "devops": "DevOps", "sql": "SQL", "nosql": "NoSQL",
    "elasticsearch": "Elasticsearch", "spark": "Spark", "hadoop": "Hadoop",
    "container orchestration": "Container Orchestration",
    "docker swarm": "Docker Swarm", "aws ecs": "AWS ECS", "ecs": "AWS ECS",
    "helm": "Helm", "cloudformation": "CloudFormation", "pulumi": "Pulumi",
}

FROM apache/airflow:2.10.3

USER root

# Install OpenJDK 17 and essential system dependencies
# Acquire::Check-Valid-Until=false and Acquire::Check-Date=false handle clock skew in container/WSL2
RUN apt-get -o Acquire::Check-Valid-Until=false -o Acquire::Check-Date=false update \
    && apt-get install -y --no-install-recommends \
        openjdk-17-jre-headless \
        procps \
        curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Dynamically link default-java for multi-arch compatibility (amd64 / arm64)
RUN ln -sfn $(ls -d /usr/lib/jvm/java-17-openjdk-* | head -n 1) /usr/lib/jvm/default-java

ENV JAVA_HOME=/usr/lib/jvm/default-java
ENV PATH="${JAVA_HOME}/bin:${PATH}"

USER airflow

# Copy and install Python requirements
COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt

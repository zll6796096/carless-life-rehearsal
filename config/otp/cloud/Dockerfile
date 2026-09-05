FROM eclipse-temurin:25-jre
WORKDIR /otp
COPY otp.jar /otp/otp.jar
COPY graph.obj /otp/data/graph.obj
COPY router-config.json /otp/data/router-config.json
ENV PORT=8080
EXPOSE 8080
CMD ["sh", "-c", "exec java -Xmx2048m -jar /otp/otp.jar --abortOnUnknownConfig --load --serve --bindAddress 0.0.0.0 --port ${PORT:-8080} /otp/data"]

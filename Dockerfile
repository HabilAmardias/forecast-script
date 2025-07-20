FROM python:3.12-slim

WORKDIR /app

COPY . ./

# Install required packages including timezone data
RUN apt-get update && apt-get -y install cron tzdata && rm -rf /var/lib/apt/lists/*

# Set timezone to GMT+7 (Asia/Jakarta)
ENV TZ=Asia/Jakarta
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r ./requirements.txt

# Create cron job for 00:00 GMT+7 (which is 17:00 UTC the previous day)
RUN echo "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" > /etc/cron.d/forecast-job && \
    echo "0 0 * * * root cd /app && /usr/local/bin/python main.py >> /var/log/cron.log 2>&1" >> /etc/cron.d/forecast-job && \
    echo "" >> /etc/cron.d/forecast-job

RUN chmod 0644 /etc/cron.d/forecast-job
RUN crontab /etc/cron.d/forecast-job
RUN touch /var/log/cron.log

# Create startup script
RUN echo '#!/bin/bash' > /start.sh && \
    echo 'echo "Starting application..."' >> /start.sh && \
    echo 'echo "Running initial execution at $(date)" >> /var/log/cron.log' >> /start.sh && \
    echo 'cd /app && /usr/local/bin/python main.py >> /var/log/cron.log 2>&1' >> /start.sh && \
    echo 'echo "Initial execution completed at $(date)" >> /var/log/cron.log' >> /start.sh && \
    echo 'service cron start' >> /start.sh && \
    echo 'echo "Cron service started at $(date)" >> /var/log/cron.log' >> /start.sh && \
    echo 'tail -f /var/log/cron.log' >> /start.sh

RUN chmod +x /start.sh

# Start with the startup script
CMD ["/start.sh"]
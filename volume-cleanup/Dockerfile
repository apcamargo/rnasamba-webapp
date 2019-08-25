FROM alpine

RUN echo "0 8 * * *  find /rnasamba-app/* -mtime +6 -type f -delete" > /etc/crontabs/root

CMD ["crond", "-l", "2", "-f"]
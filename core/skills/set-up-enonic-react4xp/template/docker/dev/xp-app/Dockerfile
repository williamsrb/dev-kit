FROM leanon/enonic-xp:{ENONIC_XP_VERSION}

ARG REPO

ENV APP_REPO=$REPO

EXPOSE 3000 3001 3005 3006

COPY launcher.sh /launcher.sh

RUN chmod +x /launcher.sh \
	&& echo "export APP_REPO=$APP_REPO" >> /etc/environment

RUN apt update && apt install -y wget
RUN wget http://nodejs.org/dist/v{NODE_XP_VERSION}/node-v{NODE_XP_VERSION}-linux-x64.tar.gz \
  && tar -C /usr/local --strip-components 1 -xzf node-v{NODE_XP_VERSION}-linux-x64.tar.gz

CMD /launcher.sh

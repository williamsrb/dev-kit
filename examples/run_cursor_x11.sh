# Permitir conexões locais ao servidor X
xhost +local:docker

docker run -d \
  --name cursor_trabalho_x11 \
  --net=host \
  --ipc=host \
  -e DISPLAY=$DISPLAY \
  -v /tmp/.X11-unix:/tmp/.X11-unix:ro \
  -v $HOME/.Xauthority:/home/developer/.Xauthority:ro \
  -v ~/cursor_perfis/perfil_trabalho/config:/home/developer/.config/Cursor \
  -v ~/cursor_perfis/perfil_trabalho/data:/home/developer/.cursor \
  -v /caminho/para/seu/projeto:/home/developer/workspace \
  cursor-ide-x11


docker run -d \
  --name cursor_pessoal_wayland \
  --ipc=host \
  -e XDG_RUNTIME_DIR=$XDG_RUNTIME_DIR \
  -e WAYLAND_DISPLAY=$WAYLAND_DISPLAY \
  -v $XDG_RUNTIME_DIR/$WAYLAND_DISPLAY:$XDG_RUNTIME_DIR/$WAYLAND_DISPLAY:ro \
  -v ~/cursor_perfis/perfil_pessoal/config:/home/developer/.config/Cursor \
  -v ~/cursor_perfis/perfil_pessoal/data:/home/developer/.cursor \
  -v /caminho/para/outro/projeto:/home/developer/workspace \
  cursor-ide-wayland


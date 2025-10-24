{
  stdenvNoCC,
  writableTmpDirAsHomeHook,

  direnv,
  direnv-instant,
  tmux,
  vhs,
}:
stdenvNoCC.mkDerivation {
  name = "demo.mp4";

  src = ./.;

  nativeBuildInputs = [
    writableTmpDirAsHomeHook

    direnv
    direnv-instant
    tmux
    vhs
  ];

  buildPhase = ''
    vhs demo.tape -o $out
  '';
}

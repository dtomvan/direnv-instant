{
  lib,
  rustPlatform,
}:

rustPlatform.buildRustPackage {
  pname = "direnv-instant";
  version = "0.1.0";

  src = lib.fileset.toSource {
    root = ./.;
    fileset = lib.fileset.unions [
      ./Cargo.toml
      ./Cargo.lock
      ./src
      ./hooks
    ];
  };

  cargoHash = "sha256-aiF9FGEcf1Drj+cg8CTiv0oKc7tDTOiK2N8qdELQLHw=";

  meta = with lib; {
    description = "Non-blocking direnv integration daemon with tmux support";
    license = licenses.mit;
    mainProgram = "direnv-instant";
  };
}

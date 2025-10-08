{
  description = "Non-blocking direnv integration daemon with tmux support";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-parts.url = "github:hercules-ci/flake-parts";
    flake-parts.inputs.nixpkgs-lib.follows = "nixpkgs";
    treefmt-nix = {
      url = "github:numtide/treefmt-nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs =
    inputs@{ flake-parts, ... }:
    flake-parts.lib.mkFlake { inherit inputs; } {
      systems = [
        "x86_64-linux"
        "aarch64-linux"
        "x86_64-darwin"
        "aarch64-darwin"
      ];

      imports = [ ./treefmt.nix ];

      perSystem =
        {
          config,
          self',
          inputs',
          pkgs,
          system,
          ...
        }:
        {
          packages.direnv-instant = pkgs.callPackage ./default.nix { };
          packages.default = self'.packages.direnv-instant;

          devShells.default = pkgs.mkShell {
            inputsFrom = [ self'.packages.direnv-instant ];
            packages = with pkgs; [
              cargo
              rustc
              rustfmt
              clippy
              rust-analyzer
            ];
          };
        };
    };
}

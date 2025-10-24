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
    flake-parts.lib.mkFlake { inherit inputs; } (
      { self, ... }:
      {
        systems = [
          "x86_64-linux"
          "aarch64-linux"
          "x86_64-darwin"
          "aarch64-darwin"
        ];

        imports = [ ./treefmt.nix ];

        perSystem =
          {
            self',
            pkgs,
            lib,
            ...
          }:
          {
            packages.direnv-instant = pkgs.callPackage ./default.nix { };
            packages.demo = pkgs.callPackage ./demo.nix { inherit (self'.packages) direnv-instant; };
            packages.default = self'.packages.direnv-instant;

            devShells.default = pkgs.mkShell {
              inputsFrom = [
                self'.packages.direnv-instant
                self'.checks.tests
              ];
              packages = with pkgs; [
                rustfmt
                clippy
                rust-analyzer
                vhs
              ];
            };

            checks =
              let
                packages = lib.mapAttrs' (n: lib.nameValuePair "package-${n}") self'.packages;
                devShells = lib.mapAttrs' (n: lib.nameValuePair "devShell-${n}") self'.devShells;
              in
              packages
              // devShells
              // {
                tests = pkgs.callPackage ./tests.nix {
                  direnv-instant = self'.packages.direnv-instant;
                };
              };
          };

        flake = {
          homeModules.direnv-instant = ./home.nix;
          homeModules.default = self.homeModules.direnv-instant;
        };
      }
    );
}

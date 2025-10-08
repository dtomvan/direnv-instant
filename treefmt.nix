{ inputs, ... }:
{
  imports = [ inputs.treefmt-nix.flakeModule ];

  perSystem =
    { ... }:
    {
      treefmt = {
        # Used to find the project root
        projectRootFile = "flake.nix";

        programs.rustfmt.enable = true;
        programs.nixfmt.enable = true;
      };
    };
}

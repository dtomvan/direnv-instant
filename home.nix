{
  pkgs,
  lib,
  config,
  ...
}:
let
  cfg = config.programs.direnv-instant;

  inherit (lib)
    mkEnableOption
    mkIf
    mkOption
    mkPackageOption
    ;

  inherit (lib.hm.shell)
    mkBashIntegrationOption
    mkZshIntegrationOption
    ;

  inherit (lib.types)
    int
    nullOr
    package
    str
    ;
in
{
  options.programs.direnv-instant = {
    enable = mkEnableOption "non-blocking direnv integration daemon with tmux support";
    package = mkPackageOption pkgs "direnv-instant" { };
    finalPackage = mkOption {
      description = "Resulting direnv-instant package";
      type = package;
      readOnly = true;
      visible = false;
    };

    enableBashIntegration = mkBashIntegrationOption { inherit config; };
    enableZshIntegration = mkZshIntegrationOption { inherit config; };

    enableKittyIntegration = (mkEnableOption "kitty integration") // {
      default = config.programs.kitty.enable;
    };

    settings = {
      use_cache = (mkEnableOption "cached environment loading for instant prompts") // {
        default = true;
      };
      mux_delay = mkOption {
        description = "Delay in seconds before spawning multiplexer pane";
        type = int;
        default = 4;
        example = 1;
      };
      debug_log = mkOption {
        description = "Path to debug log for daemon output";
        type = nullOr str;
        default = null;
        example = "/tmp/direnv-instant.log";
      };
    };
  };

  config =
    let
      finalPackage = cfg.package.overrideAttrs (prev: {
        nativeBuildInputs = (prev.nativeBuildInputs or [ ]) ++ [ pkgs.makeWrapper ];
        postInstall = (prev.postInstall or "") + ''
          wrapProgram $out/bin/direnv-instant \
            --set-default DIRENV_INSTANT_USE_CACHE ${if cfg.settings.use_cache then "1" else "0"} \
            --set-default DIRENV_INSTANT_MUX_DELAY ${builtins.toString cfg.settings.mux_delay} \
            ${
              if cfg.settings.debug_log != null then
                "--set-default DIRENV_INSTANT_DEBUG_LOG '${cfg.settings.debug_log}'"
              else
                ""
            }
        '';
      });
    in
    mkIf cfg.enable {
      programs.direnv-instant = { inherit finalPackage; };
      programs.direnv = {
        enable = lib.mkDefault true;
        # direnv and direnv-instant have mutually exclusive hooks
        enableBashIntegration = lib.mkForce (!cfg.enableBashIntegration);
        enableZshIntegration = lib.mkForce (!cfg.enableZshIntegration);
      };

      home.packages = [ finalPackage ];

      programs.bash.initExtra = mkIf cfg.enableBashIntegration ''
        eval "$(direnv-instant hook bash)"
      '';

      programs.zsh.initContent = mkIf cfg.enableZshIntegration ''
        eval "$(direnv-instant hook zsh)"
      '';

      programs.kitty.settings = mkIf cfg.enableKittyIntegration {
        allow_remote_control = true;
        listen_on = ''unix:kitty-{kitty_pid}'';
      };
    };
}

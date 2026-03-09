# Homebrew formula for SkillMeat CLI
#
# Usage with a custom tap:
#   1. Host this repo (or a dedicated tap repo) on GitHub at <user>/homebrew-skillmeat
#   2. brew tap <user>/skillmeat
#   3. brew install skillmeat
#
# Or install directly without a tap:
#   brew install --formula ./Formula/skillmeat.rb
#
# For local development (editable install), prefer:
#   pip install -e ".[dev]"

class Skillmeat < Formula
  include Language::Python::Virtualenv

  desc "Personal collection manager for Claude Code artifacts (Skills, Commands, Agents, MCP, Hooks)"
  homepage "https://github.com/miethe/skillmeat"
  url "https://files.pythonhosted.org/packages/source/s/skillmeat/skillmeat-0.9.0.tar.gz"
  sha256 "" # TODO: Replace with actual SHA256 once published to PyPI
  license "MIT"

  depends_on "python@3.12"

  # Core dependencies that pip will resolve automatically during install.
  # If you need hermetic builds, add explicit `resource` blocks for each
  # transitive dependency. For now we rely on pip's resolver within the venv.

  def install
    virtualenv_install_with_resources
  end

  test do
    assert_match version.to_s, shell_output("#{bin}/skillmeat --version")
  end
end

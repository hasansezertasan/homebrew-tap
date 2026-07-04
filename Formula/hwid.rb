class Hwid < Formula
  include Language::Python::Virtualenv

  desc "Cross-platform hardware ID extraction using native OS detection"
  homepage "https://github.com/hasansezertasan/hwid"
  url "https://files.pythonhosted.org/packages/d8/09/9db868e4f96fb07566c9fd6003a31501ef340602b4a21bc45978685d63b2/hwid-0.2.0.tar.gz"
  sha256 "462ac889a0ee302d7c2d3edf50f681c2b868e752c789fb0ee35cb357ccda0d2d"
  license "MIT"

  livecheck do
    url :stable
    strategy :pypi
  end

  depends_on "python@3.14"

  def install
    virtualenv_install_with_resources
  end

  test do
    assert_match "HWID:", shell_output("#{bin}/hwid")
  end
end

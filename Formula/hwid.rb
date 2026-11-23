class Hwid < Formula
  include Language::Python::Virtualenv

  desc "Cross-platform hardware ID extraction using native OS detection"
  homepage "https://github.com/hasansezertasan/hwid"
  url "https://files.pythonhosted.org/packages/8a/8c/80f03e58b2cfd5c96bf3b00dde129f6c58d2f03fc278232e02e432f199ea/hwid-0.4.0.tar.gz"
  sha256 "502c7ffd2bd8dfc4cbd50fe9ef8336351e9c19ea75c83e4b8f5c76789e5b4b1b"
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

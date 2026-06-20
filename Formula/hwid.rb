class Hwid < Formula
  include Language::Python::Virtualenv

  desc "Cross-platform hardware ID extraction using native OS detection"
  homepage "https://github.com/hasansezertasan/hwid"
  url "https://files.pythonhosted.org/packages/72/99/c9ba45037e00f5c1a42c7b3777ac1257c800e30b162ea66439db55e99293/hwid-0.1.0.tar.gz"
  sha256 "b9aebe2271ede00b406a15617622ecedd8eab079ec9689d3df7f5ca8510a7d2b"
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

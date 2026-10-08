import py4j.GatewayServer;
import py4j.Base64;
import com.oceanoptics.omnidriver.spectrometer.adc1000usb.ADC1000USB;
import java.io.IOException;
import java.nio.DoubleBuffer;

public class ADC1000USBGateway {
  public ADC1000USB driver;
  
  public ADC1000USBGateway() throws IOException {
	driver=new ADC1000USB();
  }
  
  public ADC1000USB getDriver() {
    return driver;
  }
  
  public DoubleBuffer getSpectrum() throws IOException {
    double[] array=driver.getSpectrum().getSpectrum();
	return DoubleBuffer.wrap(array); 
  }
  
  public static void main(String[] args) throws IOException {
    ADC1000USBGateway app = new ADC1000USBGateway();
    // app is now the gateway.entry_point
    GatewayServer server = new GatewayServer(app);
    server.start();
  }
}
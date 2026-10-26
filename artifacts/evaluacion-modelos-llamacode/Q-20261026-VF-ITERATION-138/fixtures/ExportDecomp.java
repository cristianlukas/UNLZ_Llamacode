// Ghidra post-script for the Q138 synthetic fixture.
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.program.model.listing.Function;
import ghidra.program.model.mem.MemoryBlock;
import java.io.File;
import java.io.FileOutputStream;
import java.io.OutputStreamWriter;
import java.io.PrintWriter;
import java.nio.charset.StandardCharsets;

public class ExportDecomp extends ghidra.app.script.GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length != 1) throw new IllegalArgumentException("usage: ExportDecomp.java <output.txt>");
        DecompInterface decompiler = new DecompInterface();
        if (!decompiler.openProgram(currentProgram)) throw new IllegalStateException("decompiler failed to open program");
        File output = new File(args[0]);
        output.getParentFile().mkdirs();
        try (PrintWriter writer = new PrintWriter(new OutputStreamWriter(
                new FileOutputStream(output), StandardCharsets.UTF_8))) {
            for (Function function : currentProgram.getFunctionManager().getFunctions(true)) {
                if (monitor.isCancelled()) break;
                MemoryBlock block = currentProgram.getMemory().getBlock(function.getEntryPoint());
                if (block != null && block.isExternalBlock()) continue;
                DecompileResults result = decompiler.decompileFunction(function, 30, monitor);
                writer.println("FUNCTION " + function.getName() + " @ " + function.getEntryPoint());
                if (result != null && result.decompileCompleted() && result.getDecompiledFunction() != null) {
                    writer.println(result.getDecompiledFunction().getC());
                } else {
                    writer.println("// DECOMPILATION FAILED");
                }
            }
        } finally {
            decompiler.dispose();
        }
    }
}
